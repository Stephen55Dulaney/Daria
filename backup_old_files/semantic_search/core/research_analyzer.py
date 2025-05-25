from typing import List, Dict, Any, Optional
from .vector_store import InterviewVectorStore
from .ux_analyzer import UXAnalyzer, Theme, PainPoint, Opportunity, Insight
import json
import os
from datetime import datetime

class ResearchAnalyzer:
    def __init__(self, 
                 vector_store_dir: str = "data/vector_store",
                 analysis_cache_dir: str = "data/analysis_cache"):
        """Initialize the research analyzer"""
        self.vector_store = InterviewVectorStore(vector_store_dir)
        self.ux_analyzer = UXAnalyzer()
        self.analysis_cache_dir = analysis_cache_dir
        os.makedirs(analysis_cache_dir, exist_ok=True)
    
    def index_interview(self, interview_data: Dict[str, Any]):
        """Index a new interview in the vector store"""
        # Add to vector store
        self.vector_store.add_interview(interview_data)
        
        # Analyze and cache results
        self._analyze_and_cache_interview(interview_data)
    
    def _analyze_and_cache_interview(self, interview_data: Dict[str, Any]):
        """Analyze interview and cache results"""
        interview_id = interview_data['id']
        cache_file = os.path.join(self.analysis_cache_dir, f"{interview_id}.json")
        
        # Skip if already analyzed
        if os.path.exists(cache_file):
            return
        
        # Process interview into chunks
        chunks = self.vector_store.process_interview(interview_data)
        
        # Analyze each chunk
        analyzed_chunks = []
        for chunk in chunks:
            if chunk['messages']:  # Skip empty chunks
                combined_text = ' '.join(chunk['messages'])
                analysis = self.ux_analyzer.analyze_chunk(combined_text, chunk['metadata'])
                analyzed_chunks.append(analysis)
        
        # Save analysis results
        analysis_results = {
            'interview_id': interview_id,
            'analysis_date': datetime.now().isoformat(),
            'chunks': analyzed_chunks
        }
        
        with open(cache_file, 'w') as f:
            json.dump(analysis_results, f, indent=2)
    
    def semantic_search(self,
                       query: str,
                       filters: Optional[Dict] = None,
                       analyze_results: bool = True,
                       limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search and optionally analyze results
        
        Args:
            query: Search query
            filters: Optional metadata filters
            analyze_results: Whether to run UX analysis on results
            limit: Maximum number of results
        """
        # Perform search
        results = self.vector_store.semantic_search(query, filters, limit)
        
        if analyze_results:
            # Analyze each result
            for result in results:
                analysis = self.ux_analyzer.analyze_chunk(
                    result['content'],
                    result['metadata']
                )
                result['analysis'] = analysis
        
        return results
    
    def get_interview_analysis(self, interview_id: str) -> Dict[str, Any]:
        """Get cached analysis for an interview"""
        cache_file = os.path.join(self.analysis_cache_dir, f"{interview_id}.json")
        
        if not os.path.exists(cache_file):
            raise ValueError(f"No cached analysis found for interview {interview_id}")
        
        with open(cache_file, 'r') as f:
            return json.load(f)
    
    def generate_research_summary(self, 
                                interview_ids: Optional[List[str]] = None,
                                include_quotes: bool = True) -> Dict[str, Any]:
        """
        Generate a summary of research findings
        
        Args:
            interview_ids: Optional list of interviews to include
            include_quotes: Whether to include supporting quotes
        """
        if interview_ids is None:
            interview_ids = self.vector_store.get_all_interviews()
        
        all_themes = []
        all_pain_points = []
        all_opportunities = []
        all_insights = []
        
        for interview_id in interview_ids:
            try:
                analysis = self.get_interview_analysis(interview_id)
                for chunk in analysis['chunks']:
                    all_themes.extend(chunk['themes'])
                    all_pain_points.extend(chunk['pain_points'])
                    all_opportunities.extend(chunk['opportunities'])
                    all_insights.extend(chunk['insights'])
            except Exception as e:
                print(f"Error processing interview {interview_id}: {str(e)}")
        
        # TODO: Implement theme clustering and insight aggregation
        # For now, return basic summary
        return {
            'summary': {
                'total_interviews': len(interview_ids),
                'total_insights': len(all_insights)
            },
            'themes': all_themes[:5],  # Top 5 themes
            'pain_points': all_pain_points[:5],  # Top 5 pain points
            'opportunities': all_opportunities[:5],  # Top 5 opportunities
            'key_insights': all_insights[:5]  # Top 5 insights
        }
    
    def generate_affinity_diagram(self,
                                search_results: List[Dict[str, Any]],
                                grouping_level: int = 2) -> Dict[str, Any]:
        """Generate affinity diagram from search results"""
        return self.ux_analyzer.generate_affinity_diagram(
            search_results,
            grouping_level
        ) 