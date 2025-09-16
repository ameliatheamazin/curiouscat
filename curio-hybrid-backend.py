#!/usr/bin/env python3
"""
Loads enhanced static JSON data and optionally refreshes descriptions
"""

import json
import asyncio
import aiohttp
import time
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CurioCatEnhancedBackend:
    def __init__(self, static_data_file='data.json'):
        self.static_data_file = static_data_file
        self.base_url = 'https://en.wikipedia.org/api/rest_v1'
        
        # Description cache (only for real-time description updates)
        self.description_cache = {}
        self.cache_duration = 1800  # 30 minutes cache for descriptions
        
        # Session for requests
        self.session_headers = {
            'User-Agent': 'wikiweird/1.0 (https://github.com/ameliatheamazin/wikiweird; ameliatheamazin@gmail.com)'
        }
    
    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached description is still valid"""
        if cache_key not in self.description_cache:
            return False
        
        cache_time = self.description_cache[cache_key].get('timestamp', 0)
        return (time.time() - cache_time) < self.cache_duration
    
    def load_enhanced_data(self) -> Dict:
        """Load the enhanced static JSON data with country identification"""
        try:
            with open(self.static_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded enhanced data: {len(data)} countries")
                return data
        except FileNotFoundError:
            logger.error(f"Enhanced data file {self.static_data_file} not found")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {self.static_data_file}: {e}")
            return {}
    
    def extract_wikipedia_title(self, url: str) -> str:
        """Extract the Wikipedia article title from URL"""
        if '/wiki/' in url:
            title = url.split('/wiki/')[-1]
            # Handle URL encoding
            title = title.replace('_', ' ')
            # Handle fragments and parameters
            if '#' in title:
                title = title.split('#')[0]
            if '?' in title:
                title = title.split('?')[0]
            return title.strip()
        return ""
    
    async def get_fresh_description(self, title: str) -> Optional[str]:
        """Get fresh description from Wikipedia API"""
        cache_key = f"desc_{title}"
        
        if self.is_cache_valid(cache_key):
            return self.description_cache[cache_key]['data']
        
        try:
            clean_title = title.replace(' ', '_')
            summary_url = f"{self.base_url}/page/summary/{clean_title}"
            
            async with aiohttp.ClientSession(headers=self.session_headers) as session:
                async with session.get(summary_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        description = data.get('description', '')
                        
                        # Cache the fresh description
                        self.description_cache[cache_key] = {
                            'data': description,
                            'timestamp': time.time()
                        }
                        
                        logger.debug(f"Fetched fresh description for {title}")
                        return description
                    else:
                        logger.warning(f"Wikipedia API returned {response.status} for {title}")
        except Exception as e:
            logger.error(f"Error fetching description for {title}: {e}")
        
        return None
    
    def calculate_curiosity_score(self, article: Dict) -> int:
        """Calculate curiosity score based on article characteristics"""
        score = 5  # Base score
        
        # Use enhanced data for scoring
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        categories = article.get('categories', [])
        
        # Combine text for analysis
        text_content = f"{title} {description} {' '.join(categories)}".lower()
        
        # Curiosity keywords boost
        curiosity_keywords = [
            'unusual', 'strange', 'bizarre', 'odd', 'weird', 'peculiar',
            'mysterious', 'unexplained', 'controversial', 'banned', 'illegal',
            'cult', 'conspiracy', 'hoax', 'urban legend', 'phenomenon',
            'extinct', 'abandoned', 'secret', 'hidden', 'lost', 'ancient'
        ]
        
        for keyword in curiosity_keywords:
            if keyword in text_content:
                score += 1
        
        # Country confidence boost (higher confidence = more reliable = slightly higher score)
        confidence = article.get('country_confidence', 0)
        if confidence > 0.8:
            score += 1
        
        # Categories boost (more categories = more interesting)
        category_count = len(categories)
        if category_count > 10:
            score += 2
        elif category_count > 5:
            score += 1
        
        # Cap at 10
        return min(score, 10)
    
    async def refresh_article_description(self, article: Dict, refresh_description: bool = False) -> Dict:
        """Optionally refresh article description with live data"""
        enhanced_article = article.copy()
        
        if refresh_description:
            # Extract Wikipedia title
            wiki_title = self.extract_wikipedia_title(article.get('url', ''))
            if not wiki_title:
                wiki_title = article.get('title', '')
            
            if wiki_title:
                try:
                    fresh_description = await self.get_fresh_description(wiki_title)
                    if fresh_description:
                        enhanced_article['description'] = fresh_description
                        enhanced_article['description_updated'] = datetime.now().isoformat()
                        logger.debug(f"Updated description for {wiki_title}")
                except Exception as e:
                    logger.warning(f"Failed to refresh description for {wiki_title}: {e}")
        
        # Add computed fields using enhanced data
        enhanced_article['curiosity_score'] = self.calculate_curiosity_score(enhanced_article)
        enhanced_article['last_processed'] = datetime.now().isoformat()
        
        return enhanced_article
    
    async def get_country_data(self, country: str, refresh_descriptions: bool = False, limit: int = 20) -> List[Dict]:
        """Get articles for a specific country with optional description refresh"""
        enhanced_data = self.load_enhanced_data()
        
        if not enhanced_data:
            return []
        
        # Find articles for the country (case-insensitive)
        country_articles = None
        for key, articles in enhanced_data.items():
            if key.lower() == country.lower():
                country_articles = articles
                break
        
        if not country_articles:
            logger.info(f"No articles found for {country}")
            return []
        
        # Limit articles to prevent slow responses
        articles_to_process = country_articles[:limit]
        
        logger.info(f"Processing {len(articles_to_process)} articles for {country}")
        
        # Process articles (with optional description refresh)
        processed_articles = []
        for article in articles_to_process:
            try:
                enhanced = await self.refresh_article_description(article, refresh_descriptions)
                processed_articles.append(enhanced)
                
                # Small delay between description fetches to be nice to Wikipedia
                if refresh_descriptions:
                    await asyncio.sleep(0.2)
                    
            except Exception as e:
                logger.error(f"Failed to process article {article.get('title', 'unknown')}: {e}")
                # Add article with computed fields only
                fallback = article.copy()
                fallback['curiosity_score'] = self.calculate_curiosity_score(article)
                fallback['last_processed'] = datetime.now().isoformat()
                processed_articles.append(fallback)
        
        # Sort by curiosity score, then by country confidence
        processed_articles.sort(
            key=lambda x: (
                x.get('curiosity_score', 5),
                x.get('country_confidence', 0)
            ), 
            reverse=True
        )
        
        return processed_articles
    
    def get_all_countries(self) -> List[Dict]:
        """Get list of all countries with metadata"""
        enhanced_data = self.load_enhanced_data()
        if not enhanced_data:
            return []
        
        countries_info = []
        for country, articles in enhanced_data.items():
            # Calculate country statistics
            total_articles = len(articles)
            avg_confidence = sum(art.get('country_confidence', 0) for art in articles) / total_articles if articles else 0
            
            # Count regions represented
            regions = set(art.get('source_region', 'Unknown') for art in articles)
            
            # Sample articles for preview
            sample_articles = [art.get('title', 'Unknown') for art in articles[:3]]
            
            countries_info.append({
                'country': country,
                'article_count': total_articles,
                'avg_confidence': round(avg_confidence, 2),
                'regions': list(regions),
                'sample_articles': sample_articles
            })
        
        # Sort by article count
        countries_info.sort(key=lambda x: x['article_count'], reverse=True)
        return countries_info
    
    def get_stats(self) -> Dict:
        """Get overall statistics"""
        enhanced_data = self.load_enhanced_data()
        
        if not enhanced_data:
            return {
                "total_countries": 0,
                "total_articles": 0,
                "identified_articles": 0,
                "avg_confidence": 0,
                "last_updated": "unknown"
            }
        
        # Calculate comprehensive stats
        total_articles = sum(len(articles) for articles in enhanced_data.values())
        identified_articles = total_articles - len(enhanced_data.get('Unidentified', []))
        
        # Calculate average confidence
        all_articles = []
        for articles in enhanced_data.values():
            all_articles.extend(articles)
        
        avg_confidence = sum(art.get('country_confidence', 0) for art in all_articles) / len(all_articles) if all_articles else 0
        identification_rate = (identified_articles / total_articles * 100) if total_articles > 0 else 0
        
        # Get file modification time
        try:
            import os
            last_updated = datetime.fromtimestamp(
                os.path.getmtime(self.static_data_file)
            ).isoformat()
        except:
            last_updated = "unknown"
        
        # Count regions
        regions = set()
        for articles in enhanced_data.values():
            for article in articles:
                regions.add(article.get('source_region', 'Unknown'))
        
        return {
            "total_countries": len(enhanced_data),
            "total_articles": total_articles,
            "identified_articles": identified_articles,
            "unidentified_articles": len(enhanced_data.get('Unidentified', [])),
            "identification_rate": round(identification_rate, 1),
            "avg_confidence": round(avg_confidence, 2),
            "regions_covered": list(regions),
            "last_updated": last_updated,
            "description_cache_size": len(self.description_cache)
        }
    
    def get_country_details(self, country: str) -> Optional[Dict]:
        """Get detailed information about a specific country"""
        enhanced_data = self.load_enhanced_data()
        
        # Find country (case-insensitive)
        country_articles = None
        actual_country_name = None
        for key, articles in enhanced_data.items():
            if key.lower() == country.lower():
                country_articles = articles
                actual_country_name = key
                break
        
        if not country_articles:
            return None
        
        # Analyze articles for this country
        regions = set()
        categories = set()
        confidence_scores = []
        
        for article in country_articles:
            regions.add(article.get('source_region', 'Unknown'))
            confidence_scores.append(article.get('country_confidence', 0))
            for cat in article.get('categories', []):
                categories.add(cat)
        
        return {
            'country': actual_country_name,
            'article_count': len(country_articles),
            'regions': list(regions),
            'avg_confidence': round(sum(confidence_scores) / len(confidence_scores), 2) if confidence_scores else 0,
            'min_confidence': round(min(confidence_scores), 2) if confidence_scores else 0,
            'max_confidence': round(max(confidence_scores), 2) if confidence_scores else 0,
            'top_categories': list(categories)[:20],  # Top 20 categories
            'sample_articles': [
                {
                    'title': art['title'],
                    'confidence': art.get('country_confidence', 0),
                    'region': art.get('source_region', 'Unknown')
                }
                for art in country_articles[:5]
            ]
        }


# ==================== FLASK API SERVER ====================

# Initialize the enhanced backend
backend = CurioCatEnhancedBackend()
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

@app.route('/')
def index():
    """Serve your HTML frontend"""
    return send_from_directory('.', 'main.html')

@app.route('/api/countries')
def get_countries():
    """Get all available countries with metadata"""
    try:
        countries = backend.get_all_countries()
        return jsonify({"countries": countries})
    except Exception as e:
        logger.error(f"Error getting countries: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/country/<country>')
async def get_country_articles(country):
    """Get articles for a specific country"""
    try:
        refresh_descriptions = request.args.get('refresh', 'false').lower() == 'true'
        limit = int(request.args.get('limit', '20'))
        
        # Get articles (with optional description refresh)
        articles = await backend.get_country_data(country, refresh_descriptions, limit)
        
        return jsonify({
            "country": country,
            "articles": articles,
            "count": len(articles),
            "descriptions_refreshed": refresh_descriptions,
            "limit_applied": limit
        })
    except Exception as e:
        logger.error(f"Error getting articles for {country}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/country/<country>/details')
def get_country_details(country):
    """Get detailed information about a specific country"""
    try:
        details = backend.get_country_details(country)
        if details:
            return jsonify(details)
        else:
            return jsonify({"error": "Country not found"}), 404
    except Exception as e:
        logger.error(f"Error getting details for {country}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get overall statistics"""
    try:
        stats = backend.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        enhanced_data = backend.load_enhanced_data()
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "countries_loaded": len(enhanced_data),
            "description_cache_size": len(backend.description_cache),
            "data_file": backend.static_data_file
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/clear-cache')
def clear_cache():
    """Clear the description cache"""
    try:
        cache_size = len(backend.description_cache)
        backend.description_cache.clear()
        return jsonify({
            "message": f"Description cache cleared! Removed {cache_size} items",
            "cache_size": len(backend.description_cache)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Check if enhanced data exists
    enhanced_data = backend.load_enhanced_data()
    
    if not enhanced_data:
        print("❌ No enhanced data found!")
        print(f"Please ensure {backend.static_data_file} exists")
        print("\nRun the enhanced data extractor first:")
        print("python data_extractor.py")
        print("\nExpected enhanced format:")
        print("{")
        print('  "Country Name": [')
        print('    {')
        print('      "id": "article_id",')
        print('      "title": "Article Title",')
        print('      "identified_country": "Country Name",')
        print('      "country_confidence": 0.95,')
        print('      "source_region": "Asia",')
        print('      "categories": ["Category1", "Category2"]')
        print('      ...')
        print('    }')
        print('  ]')
        print('}')
        exit(1)
    
    stats = backend.get_stats()
    
    print("✅ CurioCat Enhanced Backend Started!")
    print(f"📊 Loaded {stats['total_countries']} countries")
    print(f"📚 Total articles: {stats['total_articles']}")
    print(f"🎯 Identification rate: {stats['identification_rate']}%")
    print(f"🗂️ Data file: {backend.static_data_file}")
    
    print("\n🌐 API Endpoints:")
    print("  GET /api/countries - List all countries with metadata")
    print("  GET /api/country/<name> - Get articles (static descriptions)")
    print("  GET /api/country/<name>?refresh=true - Refresh descriptions from Wikipedia") 
    print("  GET /api/country/<name>/details - Detailed country information")
    print("  GET /api/stats - Get comprehensive statistics")
    print("  GET /api/health - Health check")
    print("  GET /api/clear-cache - Clear description cache")
    
    print("\n🐱 Frontend available at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)