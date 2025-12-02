"""
Enhanced test script with verbose logging and detailed output.

This script shows all agent execution details, tool calls, and reasoning.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

# Test data
JOB_DESCRIPTION = """
Senior Full Stack Engineer with AI Experience

We're looking for a talented engineer with:
- 5+ years of experience in full-stack development
- Strong proficiency in Python, TypeScript, and React
- Experience with AI/ML systems, particularly LLMs
- Knowledge of LangChain, LangGraph, or similar frameworks
- Experience with vector databases and RAG systems
- Strong understanding of system architecture
- Excellent communication skills

Responsibilities:
- Build AI-powered features end-to-end
- Design and implement multi-agent systems
- Work with product and clinical teams
- Mentor junior engineers
"""

RESUME_TEXT = """
John Doe
Senior Software Engineer

Experience:
- 6 years of full-stack development
- Expert in Python, JavaScript, React, and Node.js
- Built several LLM-powered applications using OpenAI and LangChain
- Implemented vector search using pgvector and Pinecone
- Strong background in system design and microservices
- Led team of 3 junior developers

Skills:
- Languages: Python, TypeScript, JavaScript, SQL
- Frameworks: React, Next.js, FastAPI, Django
- AI/ML: LangChain, OpenAI API, Sentence Transformers
- Databases: PostgreSQL, MongoDB, Redis
- Tools: Docker, Kubernetes, Git

Missing:
- No specific LangGraph experience (but has LangChain)
- Limited experience with clinical/healthcare systems
"""


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


async def test_multi_agent_verbose():
    """Test the multi-agent orchestrator with verbose output."""
    
    print_section("🤖 MULTI-AGENT RECRUITMENT ANALYSIS - VERBOSE MODE")
    
    try:
        # Import here to avoid Django setup issues
        from app.agents.orchestrator import RecruitmentOrchestrator
        from langchain_ollama import ChatOllama
        
        # Initialize LLM
        print("\n[1/5] Initializing LLM...")
        llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        print("✓ LLM initialized")
        print(f"  Model: {os.getenv('OLLAMA_MODEL', 'llama3.2')}")
        print(f"  Base URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
        
        # Initialize orchestrator
        print("\n[2/5] Initializing orchestrator...")
        orchestrator = RecruitmentOrchestrator(llm)
        print("✓ Orchestrator initialized with agents:")
        print(f"  - {orchestrator.retriever.name}")
        print(f"    Tools: {list(orchestrator.retriever.tools.keys())}")
        print(f"  - {orchestrator.analyzer.name}")
        print(f"    Tools: {list(orchestrator.analyzer.tools.keys())}")
        print(f"  - {orchestrator.interviewer.name}")
        print(f"    Tools: {list(orchestrator.interviewer.tools.keys())}")
        
        # Display input
        print_section("📋 INPUT DATA")
        print("\n📄 JOB DESCRIPTION:")
        print(JOB_DESCRIPTION[:200] + "...")
        print("\n📝 RESUME:")
        print(RESUME_TEXT[:200] + "...")
        
        # Run analysis
        print_section("⚙️  RUNNING MULTI-AGENT WORKFLOW")
        print("  (Watch the logs below for detailed execution trace)")
        print("  (This may take 30-60 seconds)\n")
        
        result = await orchestrator.arun(
            job_description=JOB_DESCRIPTION,
            resume_text=RESUME_TEXT
        )
        
        print("\n✓ Workflow completed!")
        
        # Display results
        print_section("📊 RESULTS SUMMARY")
        
        print(f"\n🎯 OVERALL MATCH: {result.match_score}/100")
        print(f"🔒 CONFIDENCE: {result.confidence_score:.2%}")
        print(f"⏱️  TOTAL TIME: {result.total_execution_time_ms}ms ({result.total_execution_time_ms/1000:.1f}s)")
        print(f"🤖 AGENTS USED: {', '.join(result.agents_used)}")
        print(f"🔧 TOOLS CALLED: {result.total_tools_called}")
        
        # Detailed analysis
        if result.detailed_analysis:
            print_section("🔍 DETAILED ANALYSIS")
            
            print(f"\n📈 MULTI-DIMENSIONAL SCORES:")
            print(f"  Technical:   {result.detailed_analysis.technical_score}/100")
            print(f"  Experience:  {result.detailed_analysis.experience_score}/100")
            print(f"  Culture Fit: {result.detailed_analysis.culture_score}/100")
            
            print(f"\n📝 SUMMARY:")
            print(f"  {result.detailed_analysis.summary}")
            
            print(f"\n❌ MISSING SKILLS ({len(result.detailed_analysis.missing_skills)}):")
            for skill in result.detailed_analysis.missing_skills:
                print(f"  - {skill}")
            
            print(f"\n✅ STRENGTHS ({len(result.detailed_analysis.strengths)}):")
            for strength in result.detailed_analysis.strengths:
                print(f"  - {strength}")
            
            print(f"\n💭 AI REASONING:")
            print(f"  {result.detailed_analysis.reasoning[:300]}...")
        
        # Interview questions
        print_section("❓ INTERVIEW QUESTIONS")
        for i, question in enumerate(result.interview_questions, 1):
            print(f"\n{i}. {question}")
        
        # Agent execution traces
        print_section("🔬 AGENT EXECUTION TRACES")
        
        for i, trace in enumerate(result.agent_traces, 1):
            print(f"\n[{i}] {trace.agent_name}")
            print(f"    ⏱️  Execution Time: {trace.execution_time_ms}ms")
            print(f"    🕐 Timestamp: {trace.timestamp}")
            
            if trace.tools_called:
                print(f"    🔧 Tools Called ({len(trace.tools_called)}):")
                for tool in trace.tools_called:
                    status = "✓" if tool.success else "✗"
                    print(f"       {status} {tool.tool_name} ({tool.execution_time_ms}ms)")
            else:
                print(f"    🔧 Tools Called: None")
            
            print(f"\n    💭 Reasoning:")
            # Print reasoning with indentation
            for line in trace.reasoning.split('\n'):
                if line.strip():
                    print(f"       {line}")
        
        # Retrieved candidates (if any)
        if result.retrieved_candidates:
            print_section("👥 RETRIEVED CANDIDATES")
            for i, candidate in enumerate(result.retrieved_candidates, 1):
                print(f"\n{i}. {candidate.name} ({candidate.email})")
                print(f"   Similarity: {candidate.similarity_score:.2%}")
        
        print_section("✅ TEST COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_multi_agent_verbose())
