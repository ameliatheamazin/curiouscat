#!/usr/bin/env python3
"""
Extracts unusual Wikipedia articles by region and enriches with metadata
Includes intelligent country/territory identification
"""

import requests
import json
import re
from time import sleep
from typing import Dict, List, Optional, Tuple
import warnings
from urllib.parse import unquote

warnings.filterwarnings('ignore')


class DataExtractor:
    """
    A class for extracting and processing unusual Wikipedia articles
    organized by geographic regions with intelligent country mapping.
    """
    
    def __init__(self, user_agent: str = 'wikiweird/1.0', rate_limit: float = 0.5):
        """
        Initialize the Data Extractor.
        
        Args:
            user_agent (str): User agent string for API requests
            rate_limit (float): Delay between API requests in seconds
        """
        self.api_url = 'https://en.wikipedia.org/w/api.php'
        self.base_url = 'https://en.wikipedia.org/api/rest_v1'
        self.user_agent = user_agent
        self.rate_limit = rate_limit
        
        # Initialize session with headers
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Define geographic regions
        self.regions = [
            'Africa', 'Antarctica', 'Asia', 'Europe', 
            'Latin America and the Caribbean', 'North America', 'Oceania'
        ]
        
        # Enhanced country/territory mappings with more comprehensive coverage
        self.region_countries = {
            'Africa': {
                'South Africa', 'Egypt', 'Nigeria', 'Kenya', 'Morocco', 'Ghana', 
                'Ethiopia', 'Tanzania', 'Algeria', 'Libya', 'Tunisia', 'Sudan', 
                'Zimbabwe', 'Botswana', 'Namibia', 'Zambia', 'Senegal', 'Mali',
                'Burkina Faso', 'Niger', 'Chad', 'Cameroon', 'Uganda', 'Rwanda',
                'Democratic Republic of the Congo', 'Republic of the Congo',
                'Central African Republic', 'Gabon', 'Equatorial Guinea',
                'São Tomé and Príncipe', 'Angola', 'Mozambique', 'Madagascar',
                'Mauritius', 'Seychelles', 'Comoros', 'Djibouti', 'Eritrea',
                'Somalia', 'Ivory Coast', 'Liberia', 'Sierra Leone', 'Guinea',
                'Guinea-Bissau', 'Gambia', 'Cape Verde', 'Benin', 'Togo',
                'Malawi', 'Lesotho', 'Eswatini', 'Burundi'
            },
            'Antarctica': {'Antarctica'},
            'Asia': {
                'China', 'Japan', 'India', 'South Korea', 'North Korea', 'Thailand', 
                'Indonesia', 'Philippines', 'Vietnam', 'Malaysia', 'Singapore',
                'Myanmar', 'Cambodia', 'Laos', 'Brunei', 'East Timor', 'Mongolia',
                'Taiwan', 'Hong Kong', 'Macau', 'Afghanistan', 'Pakistan',
                'Bangladesh', 'Sri Lanka', 'Maldives', 'Nepal', 'Bhutan',
                'Kazakhstan', 'Uzbekistan', 'Turkmenistan', 'Tajikistan',
                'Kyrgyzstan', 'Iran', 'Iraq', 'Syria', 'Lebanon', 'Jordan',
                'Israel', 'Palestine', 'Saudi Arabia', 'Yemen', 'Oman',
                'United Arab Emirates', 'Qatar', 'Bahrain', 'Kuwait', 'Turkey',
                'Cyprus', 'Georgia', 'Armenia', 'Azerbaijan', 'Russia'
            },
            'Europe': {
                'United Kingdom', 'Germany', 'France', 'Italy', 'Spain', 'Netherlands',
                'Norway', 'Sweden', 'Denmark', 'Finland', 'Iceland', 'Ireland',
                'Belgium', 'Luxembourg', 'Switzerland', 'Austria', 'Portugal',
                'Poland', 'Czech Republic', 'Slovakia', 'Hungary', 'Slovenia',
                'Croatia', 'Bosnia and Herzegovina', 'Serbia', 'Montenegro',
                'North Macedonia', 'Albania', 'Kosovo', 'Bulgaria', 'Romania',
                'Moldova', 'Ukraine', 'Belarus', 'Lithuania', 'Latvia', 'Estonia',
                'Greece', 'Malta', 'San Marino', 'Vatican City', 'Monaco',
                'Andorra', 'Liechtenstein'
            },
            'Latin America and the Caribbean': {
                'Brazil', 'Mexico', 'Argentina', 'Colombia', 'Peru', 'Chile',
                'Venezuela', 'Ecuador', 'Bolivia', 'Paraguay', 'Uruguay',
                'Guyana', 'Suriname', 'French Guiana', 'Jamaica', 'Cuba',
                'Dominican Republic', 'Haiti', 'Trinidad and Tobago', 'Barbados',
                'Bahamas', 'Belize', 'Costa Rica', 'Panama', 'Nicaragua',
                'Honduras', 'El Salvador', 'Guatemala', 'Puerto Rico',
                'Saint Lucia', 'Saint Vincent and the Grenadines', 'Grenada',
                'Antigua and Barbuda', 'Saint Kitts and Nevis', 'Dominica'
            },
            'North America': {
                'United States', 'Canada', 'Greenland'
            },
            'Oceania': {
                'Australia', 'New Zealand', 'Fiji', 'Papua New Guinea', 'Samoa',
                'Tonga', 'Vanuatu', 'Solomon Islands', 'Palau', 'Marshall Islands',
                'Micronesia', 'Kiribati', 'Tuvalu', 'Nauru', 'Cook Islands'
            }
        }
        
        # Country/territory synonyms and alternative names
        self.country_synonyms = {
            'USA': 'United States',
            'US': 'United States',
            'America': 'United States',
            'UK': 'United Kingdom',
            'Britain': 'United Kingdom',
            'England': 'United Kingdom',
            'Scotland': 'United Kingdom',
            'Wales': 'United Kingdom',
            'Northern Ireland': 'United Kingdom',
            'PRC': 'China',
            "People's Republic of China": 'China',
            'ROC': 'Taiwan',
            'Republic of China': 'Taiwan',
            'South Korea': 'South Korea',
            'Republic of Korea': 'South Korea',
            'North Korea': 'North Korea',
            'DPRK': 'North Korea',
            'UAE': 'United Arab Emirates',
            'Czech Republic': 'Czech Republic',
            'Czechia': 'Czech Republic',
            'DRC': 'Democratic Republic of the Congo',
            'Congo-Kinshasa': 'Democratic Republic of the Congo',
            'Congo-Brazzaville': 'Republic of the Congo',
        }
        
        # Prefixes to skip when filtering articles
        self.skip_prefixes = [
            'file:', 'image:', 'category:', 'wp:', 'wikipedia:', 
            'template:', ':category:', 'commons:'
        ]
    
    def get_subpage_content(self, subpage_name: str) -> Optional[str]:
        """
        Fetch content from a Wikipedia subpage.
        
        Args:
            subpage_name (str): Name of the subpage to fetch
            
        Returns:
            Optional[str]: Content of the subpage or None if failed
        """
        try:
            full_page_name = f"Wikipedia:Unusual_articles/{subpage_name}"
            print(f"📄 Fetching: {full_page_name}")
            
            params = {
                'action': 'parse',
                'page': full_page_name,
                'format': 'json',
                'prop': 'wikitext'
            }
            
            response = self.session.get(self.api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if 'parse' in data and 'wikitext' in data['parse']:
                content = data['parse']['wikitext']['*']
                print(f"✅ Successfully fetched ({len(content)} characters)")
                return content
            else:
                print("❌ No wikitext found in response")
                return None
                
        except Exception as e:
            print(f"❌ Error getting subpage {subpage_name}: {e}")
            return None
    
    def extract_articles_from_section(self, section_content: str, region_name: str) -> List[str]:
        """
        Extract article links from a section's content.
        
        Args:
            section_content (str): Raw content of the section
            region_name (str): Name of the region for logging
            
        Returns:
            List[str]: List of unique article titles
        """
        # Find all wikilinks [[Article Name]] or [[Article Name|Display Text]]
        article_pattern = r'\[\[([^|\]]+)(?:\|[^\]]+)?\]\]'
        matches = re.findall(article_pattern, section_content)
        
        # Filter out non-article links
        articles = []
        for match in matches:
            article = match.strip()
            if article and not any(article.lower().startswith(prefix) for prefix in self.skip_prefixes):
                # Skip section headers and other meta content
                if not re.match(r'^(Category|Template|Help|Wikipedia):', article, re.IGNORECASE):
                    articles.append(article)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_articles = []
        for article in articles:
            if article not in seen:
                seen.add(article)
                unique_articles.append(article)
        
        print(f"   🔍 Found {len(unique_articles)} unique articles in {region_name}")
        if unique_articles:
            print(f"   Examples: {', '.join(unique_articles[:3])}{'...' if len(unique_articles) > 3 else ''}")
        
        return unique_articles
    
    def parse_geographic_sections(self, content: str) -> Dict[str, List[str]]:
        """
        Parse geographic sections from the Places and infrastructure content.
        
        Args:
            content (str): Raw content from the Wikipedia page
            
        Returns:
            Dict[str, List[str]]: Dictionary mapping regions to article lists
        """
        if not content:
            return {}
        
        geographic_articles = {}
        print("🔍 Looking for geographic sections...")
        
        for region in self.regions:
            # Create flexible pattern for region headers
            region_escaped = re.escape(region)
            pattern = rf'===\s*{region_escaped}\s*===(.*?)(?====|\Z)'
            
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            
            if match:
                section_content = match.group(1)
                print(f"✅ Found section: {region}")
                print(f"   Section content length: {len(section_content)} characters")
                
                # Extract articles from this section
                articles = self.extract_articles_from_section(section_content, region)
                if articles:
                    geographic_articles[region] = articles
                    print(f"   📚 Extracted {len(articles)} articles")
                else:
                    print(f"   ⚠️  No articles found in section")
            else:
                print(f"❌ Section not found: {region}")
        
        return geographic_articles
    
    def get_article_categories(self, article_title: str) -> List[str]:
        """
        Get categories for an article to help identify its country/location.
        
        Args:
            article_title (str): Title of the Wikipedia article
            
        Returns:
            List[str]: List of category names
        """
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': article_title,
                'prop': 'categories',
                'cllimit': 'max'
            }
            
            response = self.session.get(self.api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            pages = data.get('query', {}).get('pages', {})
            
            categories = []
            for page_data in pages.values():
                if 'categories' in page_data:
                    for cat in page_data['categories']:
                        categories.append(cat['title'].replace('Category:', ''))
            
            return categories
            
        except Exception as e:
            print(f"   ⚠️ Error getting categories for {article_title}: {e}")
            return []
    
    def identify_country_from_context(self, article_title: str, article_extract: str, 
                                    categories: List[str], region: str) -> Tuple[Optional[str], float]:
        """
        Identify the most likely country/territory for an article using multiple signals.
        
        Args:
            article_title (str): Title of the article
            article_extract (str): Extract/summary text
            categories (List[str]): Wikipedia categories
            region (str): Source region
            
        Returns:
            Tuple[Optional[str], float]: (country_name, confidence_score)
        """
        # Combine all text for analysis
        full_text = f"{article_title} {article_extract} {' '.join(categories)}".lower()
        
        # Get potential countries from the region
        region_countries = self.region_countries.get(region, set())
        
        country_scores = {}
        
        # Score countries based on mentions in text
        for country in region_countries:
            score = 0.0
            country_lower = country.lower()
            
            # Direct country name mentions
            country_mentions = len(re.findall(rf'\b{re.escape(country_lower)}\b', full_text))
            score += country_mentions * 10
            
            # Category-based scoring (higher weight)
            for category in categories:
                cat_lower = category.lower()
                if country_lower in cat_lower:
                    score += 20
                    # Special patterns for locations
                    if any(pattern in cat_lower for pattern in ['in ' + country_lower, 
                                                               country_lower + ' ', 
                                                               'of ' + country_lower]):
                        score += 30
            
            # Title-based scoring
            if country_lower in article_title.lower():
                score += 15
            
            # Extract-based scoring  
            if country_lower in article_extract.lower():
                score += 5
            
            if score > 0:
                country_scores[country] = score
        
        # Also check synonyms
        for synonym, canonical in self.country_synonyms.items():
            if canonical in region_countries:
                synonym_lower = synonym.lower()
                if synonym_lower in full_text:
                    country_scores[canonical] = country_scores.get(canonical, 0) + 8
        
        # Special handling for cities/territories that are commonly misidentified
        self._apply_special_location_rules(full_text, categories, country_scores, region)
        
        if not country_scores:
            return None, 0.0
        
        # Return the country with highest score
        best_country = max(country_scores, key=country_scores.get)
        confidence = min(country_scores[best_country] / 50.0, 1.0)  # Normalize to 0-1
        
        return best_country, confidence
    
    def _apply_special_location_rules(self, full_text: str, categories: List[str], 
                                    country_scores: Dict[str, float], region: str):
        """Apply special rules for commonly confused locations."""
        
        # Hong Kong and Macau
        if 'hong kong' in full_text:
            country_scores['Hong Kong'] = country_scores.get('Hong Kong', 0) + 50
        if 'macau' in full_text or 'macao' in full_text:
            country_scores['Macau'] = country_scores.get('Macau', 0) + 50
            
        # Taiwan vs China
        if 'taiwan' in full_text or 'republic of china' in full_text:
            country_scores['Taiwan'] = country_scores.get('Taiwan', 0) + 40
        elif 'mainland china' in full_text or "people's republic" in full_text:
            country_scores['China'] = country_scores.get('China', 0) + 40
            
        # UK constituent countries
        if any(term in full_text for term in ['england', 'english', 'london']):
            country_scores['United Kingdom'] = country_scores.get('United Kingdom', 0) + 30
        if any(term in full_text for term in ['scotland', 'scottish', 'edinburgh']):
            country_scores['United Kingdom'] = country_scores.get('United Kingdom', 0) + 30
        if any(term in full_text for term in ['wales', 'welsh', 'cardiff']):
            country_scores['United Kingdom'] = country_scores.get('United Kingdom', 0) + 30
        if 'northern ireland' in full_text:
            country_scores['United Kingdom'] = country_scores.get('United Kingdom', 0) + 30
            
        # US vs other North American countries
        if region == 'North America':
            if any(term in full_text for term in ['united states', ' usa ', ' us ', 'american']):
                country_scores['United States'] = country_scores.get('United States', 0) + 25
            elif any(term in full_text for term in ['canada', 'canadian']):
                country_scores['Canada'] = country_scores.get('Canada', 0) + 25
    
    def get_enhanced_article_info(self, article_title: str, region: str) -> Dict:
        """
        Get enhanced article info including intelligent country identification.
        
        Args:
            article_title (str): Title of the Wikipedia article
            region (str): Source region
            
        Returns:
            Dict: Enhanced article metadata with country identification
        """
        try:
            clean_title = article_title.replace(' ', '_')
            summary_url = f"{self.base_url}/page/summary/{clean_title}"
            response = self.session.get(summary_url)
            
            basic_info = {
                'title': article_title,
                'description': 'Unusual Wikipedia article',
                'extract': '',
                'url': f"https://en.wikipedia.org/wiki/{clean_title}",
                'thumbnail': None
            }
            
            if response.status_code == 200:
                data = response.json()
                basic_info.update({
                    'title': data.get('title', article_title),
                    'description': data.get('description', ''),
                    'extract': data.get('extract', ''),
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', 
                          f"https://en.wikipedia.org/wiki/{clean_title}"),
                    'thumbnail': data.get('thumbnail', {}).get('source') if data.get('thumbnail') else None
                })
            
            # Get categories for better country identification
            categories = self.get_article_categories(article_title)
            
            # Identify the most likely country
            country, confidence = self.identify_country_from_context(
                article_title, basic_info['extract'], categories, region
            )
            
            # Enhanced article info with location intelligence
            enhanced_info = {
                'id': f"{article_title.lower().replace(' ', '_')}",
                'title': basic_info['title'],
                'description': basic_info['description'],
                'extract': (basic_info['extract'][:300] + '...' 
                          if len(basic_info['extract']) > 300 
                          else basic_info['extract']),
                'url': basic_info['url'],
                'thumbnail': basic_info['thumbnail'],
                'source_region': region,
                'identified_country': country,
                'country_confidence': round(confidence, 2),
                'categories': categories[:10],  # Top 10 categories
                'location_signals': {
                    'has_geographic_categories': any('geography' in cat.lower() or 'location' in cat.lower() 
                                                   for cat in categories),
                    'category_count': len(categories)
                }
            }
            
            return enhanced_info
            
        except Exception as e:
            print(f"⚠️ Error getting enhanced info for {article_title}: {e}")
            return self._create_fallback_enhanced_info(article_title, region)
    
    def _create_fallback_enhanced_info(self, article_title: str, region: str) -> Dict:
        """Create fallback enhanced article info when API fails."""
        clean_title = article_title.replace(' ', '_')
        return {
            'id': f"{article_title.lower().replace(' ', '_')}",
            'title': article_title,
            'description': 'Unusual Wikipedia article',
            'extract': '',
            'url': f"https://en.wikipedia.org/wiki/{clean_title}",
            'thumbnail': None,
            'source_region': region,
            'identified_country': None,
            'country_confidence': 0.0,
            'categories': [],
            'location_signals': {
                'has_geographic_categories': False,
                'category_count': 0
            }
        }
    
    def organize_by_countries(self, regional_articles: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
        """
        Process articles and organize them by intelligently identified countries.
        
        Args:
            regional_articles (Dict[str, List[str]]): Articles organized by region
            
        Returns:
            Dict[str, List[Dict]]: Articles organized by identified countries
        """
        country_articles = {}
        unidentified_articles = []
        
        total_articles = sum(len(articles) for articles in regional_articles.values())
        processed = 0
        
        print(f"🌍 Processing {total_articles} articles with intelligent country identification...")
        
        for region, articles in regional_articles.items():
            print(f"\n📍 Processing {region} ({len(articles)} articles)")
            
            for article_title in articles:
                processed += 1
                print(f"   🔍 {processed}/{total_articles}: {article_title}")
                
                # Get enhanced article info with country identification
                article_info = self.get_enhanced_article_info(article_title, region)
                
                identified_country = article_info['identified_country']
                
                if identified_country and article_info['country_confidence'] > 0.1:
                    # High enough confidence to assign to a country
                    if identified_country not in country_articles:
                        country_articles[identified_country] = []
                    
                    country_articles[identified_country].append(article_info)
                    print(f"      → {identified_country} (confidence: {article_info['country_confidence']})")
                else:
                    # Low confidence or no identification - keep in unidentified list
                    unidentified_articles.append(article_info)
                    print(f"      → Unidentified (confidence: {article_info['country_confidence']})")
                
                sleep(self.rate_limit)
        
        # Add unidentified articles to a special category
        if unidentified_articles:
            country_articles['Unidentified'] = unidentified_articles
        
        return country_articles
    
    def save_to_json(self, data: Dict, filename: str = 'data.json'):
        """
        Save data to JSON file.
        
        Args:
            data (Dict): Data to save
            filename (str): Output filename
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved enhanced data to '{filename}'")
        except Exception as e:
            print(f"❌ Error saving to {filename}: {e}")
    
    def process_all_data(self, max_articles_per_region: int = None) -> Dict[str, List[Dict]]:
        """
        Complete processing pipeline with intelligent country identification.
        
        Args:
            max_articles_per_region (int, optional): Limit articles per region for testing
            
        Returns:
            Dict[str, List[Dict]]: Complete dataset organized by identified countries
        """
        
        # 1. Fetch subpage content
        places_content = self.get_subpage_content("Places and infrastructure")
        if not places_content:
            print("❌ Failed to get content - stopping here")
            return {}
        
        # 2. Parse geographic sections
        regional_articles = self.parse_geographic_sections(places_content)
        if not regional_articles:
            print("❌ No geographic articles found")
            return {}
        
        # Limit articles for testing if specified
        if max_articles_per_region:
            for region in regional_articles:
                regional_articles[region] = regional_articles[region][:max_articles_per_region]
        
        print(f"\n📊 PARSING RESULTS:")
        print(f"Regions found: {len(regional_articles)}")
        total_articles = sum(len(articles) for articles in regional_articles.values())
        print(f"Total articles: {total_articles}")
        
        # 3. Organize by intelligently identified countries
        country_articles = self.organize_by_countries(regional_articles)
        
        return country_articles
    
    def print_summary(self, data: Dict[str, List[Dict]]):
        """
        Print detailed summary statistics of the processed data.
        
        Args:
            data (Dict[str, List[Dict]]): Processed data to summarize
        """
        if not data:
            print("❌ No data to summarize")
            return
        
        total_articles = sum(len(articles) for articles in data.values())
        identified_articles = sum(len(articles) for country, articles in data.items() 
                                if country != 'Unidentified')
        unidentified_count = len(data.get('Unidentified', []))
        
        print(f"\n🎉 PROCESSING COMPLETE!")
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"Total articles processed: {total_articles}")
        print(f"Successfully identified: {identified_articles}")
        print(f"Unidentified: {unidentified_count}")
        print(f"Identification rate: {(identified_articles/total_articles*100):.1f}%")
        
        print(f"\n🌍 Countries/Territories with articles:")
        for country, articles in sorted(data.items()):
            if country != 'Unidentified':
                avg_confidence = sum(art['country_confidence'] for art in articles) / len(articles)
                print(f"  {country}: {len(articles)} articles (avg confidence: {avg_confidence:.2f})")
        
        if unidentified_count > 0:
            print(f"\n❓ Unidentified articles: {unidentified_count}")
            print("  These articles need manual review for country assignment")


def main():
    """Main execution function."""
    # Initialize enhanced extractor
    extractor = DataExtractor(rate_limit=0.8)  # Slightly slower for API stability
    
    # Process all data (limit for demo - remove limit for full processing)
    data = extractor.process_all_data(max_articles_per_region=5)
    
    # Save to JSON
    if data:
        extractor.save_to_json(data)
        extractor.print_summary(data)
    else:
        print("❌ No data was processed")


if __name__ == "__main__":
    main()