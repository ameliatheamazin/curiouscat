# 🌍 CurioMap

CurioMap is a lightweight web app that visualizes **unusual Wikipedia articles** on an interactive world map.  
It’s designed for curious minds and travelers who want to explore quirky, strange, and fascinating facts tied to different countries and regions.

---

## 📖 Project Walkthrough

### 1. What is CurioMap?
CurioMap brings together unusual Wikipedia articles and geography. By plotting these quirky facts on a map, users can:
- Explore by country or region
- Discover surprising cultural tidbits, oddities, and strange history
- Use the map as inspiration for travel or curiosity-driven browsing

---

### 2. Data Source

- **Primary Source**: [Wikipedia: Unusual articles](https://en.wikipedia.org/wiki/Wikipedia:Unusual_articles)  
- **Processing**:  
  - Extract **Country**, **Article Title**, and **Description**  
  - Enrich with metadata (links, structured info) using the **Wikipedia API** and **Wikidata SPARQL**  
- **Data Format**: JSON or small local DB (SQLite) for fast loading  

---

### 3. Methodology

1. **Data Collection**  
   Scrape and clean Wikipedia’s unusual articles list, then map them to countries/regions.  

2. **Data Enrichment**  
   Use the Wikipedia library + API to fetch accurate descriptions and direct links.  

3. **Visualization**  
   - Interactive world map built with **Leaflet.js** (lightweight) or **Mapbox**  
   - Clickable countries and zoomable regions  
   - Popups with article title, description, and Wikipedia link  

4. **User Interface**  
   - Fullscreen map with optional left-side info panel  
   - Mobile-responsive, playful, light theme  

---

### 4. Technical Stack

| Component     | Choice                                 |
| ------------- | -------------------------------------- |
| Frontend      | HTML/CSS + JavaScript (Vanilla or React) |
| Map Library   | Leaflet.js (lightweight) or Mapbox     |
| Backend       | Optional (static JSON for MVP)         |
| Data Storage  | JSON or SQLite                         |
| Wikipedia API | MediaWiki + Wikidata SPARQL            |

---

### 5. Key Takeaways

- 📌 **CurioMap bridges geography with curiosity**: A fun way to explore the world through unusual knowledge.  
- ⚡ **Lightweight MVP-first design**: Uses static JSON to remain fast and accessible.  
- 🌐 **Direct Wikipedia integration**: Ensures accurate, up-to-date information.  
- 🚀 **Expandable**: Future stretch goals include topic filters, user-submitted articles, and weird travel guides.  

---

## ✅ Success Criteria

- Users can click on a country and see at least one unusual article  
- Map loads quickly and is responsive on desktop and mobile  
- Popups link to the original Wikipedia pages  
- Open-source friendly with clean, maintainable code  

---

## 🎯 Stretch Goals

- Filter by themes (e.g., “Weird Laws”, “Odd Museums”)  
- Curated “Weird Travel Guides” for travelers  
- User-submitted suggestions and crowdsourced curation  

---

## 🔗 Inspiration

This project combines open knowledge (Wikipedia) with interactive mapping to encourage exploration, learning, and delight in the weirdness of the world. 🌍✨
