import os
import json
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.models import ScreeningRequest, ScreeningResponse
from app.prompts import RESUME_SCREENING_PROMPT


class ResumeScreeningService:
    """Service for screening resumes using LLM."""

    def __init__(self):
        """Initialize the screening service with LLM."""
        llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()

        if llm_provider == "ollama":
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")

            self.llm = ChatOllama(
                model=ollama_model, base_url=ollama_base_url, format="json"
            )
            print(f"✓ Using Ollama with model: {ollama_model}")
            self.use_ollama = True

        elif llm_provider == "openai":
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required when using OpenAI provider"
                )

            openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

            self.llm = ChatOpenAI(
                model=openai_model, temperature=0.3, openai_api_key=openai_api_key
            )
            print(f"✓ Using OpenAI with model: {openai_model}")
            self.use_ollama = False

        else:
            raise ValueError(
                f"Unsupported LLM provider: {llm_provider}. Use 'ollama' or 'openai'"
            )

        # Initialize the output parser
        self.parser = PydanticOutputParser(pydantic_object=ScreeningResponse)

        # Create the prompt template from imported prompt
        self.prompt_template = PromptTemplate(
            template=RESUME_SCREENING_PROMPT,
            input_variables=["job_description", "resume_text"],
        )

        # Create the chain
        self.chain = self.prompt_template | self.llm

    async def analyze(
        self, job_description: str, resume_text: str
    ) -> ScreeningResponse:
        """
        Analyze a resume against a job description.

        Args:
            job_description: The job description text
            resume_text: The resume/CV text

        Returns:
            ScreeningResponse with structured evaluation
        """
        try:
            # Get the raw response
            result = await self.chain.ainvoke(
                {"job_description": job_description, "resume_text": resume_text}
            )
        except Exception as e:
            error_msg = str(e)
            if "Connection" in error_msg or "refused" in error_msg:
                raise ConnectionError(
                    f"Cannot connect to LLM service. "
                    f"Please ensure Ollama is running at {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}. "
                    f"Error: {error_msg}"
                )
            raise

        # Extract content based on response type
        if hasattr(result, "content"):
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
            raise ValueError(
                f"Failed to create ScreeningResponse: {e}\nData: {data if 'data' in locals() else content}"
            )
