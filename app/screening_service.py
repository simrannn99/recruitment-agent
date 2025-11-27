import os
import json
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from app.models import ScreeningResponse


class ResumeScreeningService:
    """Service for analyzing resumes against job descriptions using LLM."""
    
    def __init__(self):
        """Initialize the screening service with LLM and prompt template."""
        # Get LLM provider from environment (default to ollama)
        llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        
        # Initialize the LLM based on provider
        if llm_provider == "ollama":
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
            
            self.llm = ChatOllama(
                model=ollama_model,
                base_url=ollama_base_url,
                temperature=0.3,
                format="json"  # Force JSON output
            )
            print(f"✓ Using Ollama locally with model: {ollama_model}")
            self.use_ollama = True
            
        elif llm_provider == "openai":
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required when using OpenAI provider")
            
            openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            
            self.llm = ChatOpenAI(
                model=openai_model,
                temperature=0.3,
                openai_api_key=openai_api_key
            )
            print(f"✓ Using OpenAI with model: {openai_model}")
            self.use_ollama = False
            
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}. Use 'ollama' or 'openai'")
        
        # Initialize the output parser
        self.parser = PydanticOutputParser(pydantic_object=ScreeningResponse)
        
        # Create the prompt template with explicit JSON formatting
        self.prompt_template = PromptTemplate(
            template="""You are a Senior Tech Recruiter with extensive experience in evaluating candidates.

Your task is to analyze the following resume against the job description and provide a structured evaluation.

Job Description:
{job_description}

Resume:
{resume_text}

Please analyze the resume and provide your response in the following JSON format ONLY. Do not include any text before or after the JSON:

{{
  "match_score": <number between 0-100>,
  "summary": "<brief 2-sentence summary of candidate fit>",
  "missing_skills": ["<skill1>", "<skill2>", ...],
  "interview_questions": ["<question1>", "<question2>", "<question3>"]
}}

Requirements:
1. match_score: A number from 0 to 100 indicating how well the candidate fits the role
2. summary: Maximum 2 sentences describing the candidate's fit
3. missing_skills: List of key skills from the job description that are missing from the resume
4. interview_questions: Exactly 3 specific, role-relevant questions to assess the candidate

IMPORTANT: Return ONLY valid JSON. No additional text, explanations, or markdown formatting.
""",
            input_variables=["job_description", "resume_text"]
        )
        
        # Create the chain
        self.chain = self.prompt_template | self.llm
    
    async def analyze(self, job_description: str, resume_text: str) -> ScreeningResponse:
        """
        Analyze a resume against a job description.
        
        Args:
            job_description: The job description text
            resume_text: The resume/CV text
            
        Returns:
            ScreeningResponse with structured evaluation
        """
        # Get the raw response
        result = await self.chain.ainvoke({
            "job_description": job_description,
            "resume_text": resume_text
        })
        
        # Extract content based on response type
        if hasattr(result, 'content'):
            content = result.content
        else:
            content = str(result)
        
        # Parse JSON response
        try:
            # Clean the response (remove markdown code blocks if present)
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            data = json.loads(content)
            
            # Validate and create response
            return ScreeningResponse(**data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {content}")
        except Exception as e:
            raise ValueError(f"Failed to create ScreeningResponse: {e}\nData: {data if 'data' in locals() else content}")

