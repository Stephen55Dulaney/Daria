import json
import os
from core.research_analyzer import ResearchAnalyzer

def load_interview(file_path: str) -> dict:
    """Load interview data from JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def main():
    # Initialize the research analyzer
    analyzer = ResearchAnalyzer()
    
    # Load and index sample interview
    interview_path = os.path.join('data', 'interviews', 'sessions', 
                                '99a4c906-1d83-4470-9a8e-ab3af10bb72b.json')
    interview_data = load_interview(interview_path)
    
    print(f"Indexing interview: {interview_data['id']}")
    analyzer.index_interview(interview_data)
    
    # Perform semantic search
    print("\nSearching for pain points...")
    results = analyzer.semantic_search(
        query="user frustration or difficulty",
        filters={"speaker_type": "participant"},
        analyze_results=True,
        limit=3
    )
    
    # Print results
    print("\nSearch Results:")
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"Content: {result['content'][:200]}...")
        print(f"Speaker: {result['metadata']['speaker']}")
        print(f"Timestamp: {result['metadata']['timestamp']}")
        
        if 'analysis' in result:
            analysis = result['analysis']
            print("\nAnalysis:")
            print(f"Primary Theme: {analysis['themes'].primary}")
            print("Pain Points:")
            for pain_point in analysis['pain_points']:
                print(f"- {pain_point.description} (Severity: {pain_point.severity})")
            print("Opportunities:")
            for opportunity in analysis['opportunities']:
                print(f"- {opportunity.description}")
    
    # Generate research summary
    print("\nGenerating Research Summary...")
    summary = analyzer.generate_research_summary()
    
    print("\nResearch Summary:")
    print(f"Total Interviews: {summary['summary']['total_interviews']}")
    print(f"Total Insights: {summary['summary']['total_insights']}")
    print("\nTop Themes:")
    for theme in summary['themes']:
        print(f"- {theme.primary} (Confidence: {theme.confidence})")

if __name__ == "__main__":
    main() 