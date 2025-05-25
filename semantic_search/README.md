# UX Research Semantic Search Tool

A modern tool for searching and analyzing UX research insights using semantic search and AI-powered analysis.

## Features

- **Semantic Search**: Search through interview transcripts and research data using natural language queries
- **AI-Powered Analysis**: Extract insights, themes, and patterns from research data using GPT-4
- **Interactive UI**: Modern React interface with Material UI components and smooth animations
- **Affinity Diagrams**: Automatically generate and visualize affinity diagrams from research insights
- **Research Analytics**: Track and analyze research trends and patterns

## Tech Stack

- **Frontend**: Next.js, React, Material UI, Framer Motion
- **Backend**: Next.js API Routes
- **AI/ML**: OpenAI GPT-4, ChromaDB for vector search
- **Language**: TypeScript

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Set up environment variables:
   ```bash
   cp .env.example .env.local
   ```
   Then add your OpenAI API key to `.env.local`

4. Run the development server:
   ```bash
   npm run dev
   ```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
semantic_search/
├── core/                   # Core functionality
│   ├── research_analyzer.py  # Research analysis logic
│   ├── llm_analyzer.py      # LLM integration
│   └── vector_store.py      # Vector search implementation
├── frontend/              # Frontend components
│   ├── components/         # React components
│   └── pages/             # Next.js pages
│       └── api/           # API routes
├── data/                  # Data storage
└── public/               # Static assets
```

## Features in Detail

### Semantic Search
- Natural language search through research data
- Relevance-based ranking of results
- Filter by insight type, confidence level, etc.

### AI Analysis
- Theme identification
- Pain point detection
- Opportunity extraction
- Insight classification

### Affinity Diagrams
- Automatic grouping of related insights
- Interactive visualization
- Exportable formats

### Analytics
- Research coverage analysis
- Trend identification
- Impact assessment

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 