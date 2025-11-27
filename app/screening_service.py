import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.models import ScreeningResponse


class ResumeScreeningService:
    """Service for analyzing resumes against job descriptions using LLM."""
    
    def __init__(self):
        """Initialize the screening service with LLM and prompt template."""
        # Initialize the LLM
        self.llm = ChatOpenAI(
            model="gpt-5-mini",
            temperature=0.3,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize the output parser
        self.parser = PydanticOutputParser(pydantic_object=ScreeningResponse)
        
        # Create the prompt template
        self.prompt_template = PromptTemplate(
            template="""You are a Senior Tech Recruiter with extensive experience in evaluating candidates.

Your task is to analyze the following resume against the job description and provide a structured evaluation.

Job Description:
{job_description}

Resume:
{resume_text}

Please analyze the resume and provide:
1. A match score (0-100) indicating how well the candidate fits the role
2. A brief summary (maximum 2 sentences) of the candidate's fit
3. A list of key skills mentioned in the job description that are missing from the resume
4. Exactly 3 specific, role-relevant interview questions to assess the candidate

Be thorough, fair, and specific in your evaluation.

{format_instructions}
""",
            input_variables=["job_description", "resume_text"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        # Create the chain
        self.chain = self.prompt_template | self.llm | self.parser
    
    async def analyze(self, job_description: str, resume_text: str) -> ScreeningResponse:
        """
        Analyze a resume against a job description.
        
        Args:
            job_description: The job description text
            resume_text: The resume/CV text
            
        Returns:
            ScreeningResponse with structured evaluation
        """
        result = await self.chain.ainvoke({
            "job_description": job_description,
            "resume_text": resume_text
        })
        
        return result
