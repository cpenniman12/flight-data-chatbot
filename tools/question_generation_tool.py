"""
Question Generation Tool

This module implements a tool that generates follow-up questions based on previous queries and results.
"""

import logging
from typing import Dict, Any, List, Optional

import anthropic

from tools.base_tool import BaseTool, ToolParameter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class QuestionGenerationTool(BaseTool):
    """Tool for generating follow-up questions based on previous queries and results."""

    def __init__(self, client: anthropic.Anthropic):
        """
        Initialize the QuestionGenerationTool.
        
        Args:
            client: The Anthropic client
        """
        super().__init__(
            name="generate_follow_up_questions",
            description="Generates follow-up questions based on previous queries and results",
            parameters=[
                ToolParameter(
                    name="current_query",
                    description="The current user query",
                    param_type="string",
                    required=True
                ),
                ToolParameter(
                    name="results",
                    description="The results from the current query",
                    param_type="array",
                    required=True
                ),
                ToolParameter(
                    name="columns",
                    description="The column metadata for the results",
                    param_type="array",
                    required=True
                ),
                ToolParameter(
                    name="conversation_history",
                    description="Previous conversation for context",
                    param_type="array",
                    required=False,
                    default=[]
                )
            ]
        )
        self.client = client
        
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the question generation tool.
        
        Args:
            **kwargs: The parameters for the tool
                - current_query: The current user query
                - results: The results from the current query
                - columns: The column metadata for the results
                - conversation_history: Optional conversation history
                
        Returns:
            A dictionary with generated follow-up questions
        """
        # Validate parameters
        params = self.validate_parameters(kwargs)
        current_query = params["current_query"]
        results = params["results"]
        columns = params["columns"]
        conversation_history = params.get("conversation_history", [])
        
        # Check if we have results to analyze
        if not results:
            return {
                "questions": [
                    "What other aspects of NYC flights would you like to explore?",
                    "Would you like to see flight delays by carrier?",
                    "Would you like to learn about the busiest airports in NYC?"
                ],
                "status": "fallback"
            }
        
        # Create a sample of the results to avoid context overflow
        max_sample_size = 5
        results_sample = results[:max_sample_size]
        
        # Build conversation context
        conversation_context = ""
        if conversation_history:
            conversation_context = "Previous conversation (up to 3 most recent exchanges):\n"
            # Only include the 3 most recent exchanges
            recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
            for msg in recent_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    conversation_context += f"User: {content}\n"
                else:
                    # Truncate long assistant messages
                    if len(content) > 300:
                        content = content[:300] + "..."
                    conversation_context += f"Assistant: {content}\n"
            conversation_context += "\n"
        
        # Create the prompt
        prompt = f"""Generate 3 insightful follow-up questions based on the following user query and data:

User query: {current_query}

Available columns in the data: {[col['name'] for col in columns]}

Sample results (up to {max_sample_size} rows):
{str(results_sample)}

{conversation_context}

Generate 3 follow-up questions that would:
1. Deepen the analysis of the current data
2. Explore related aspects not covered in the current query
3. Offer a different perspective or comparison

IMPORTANT RULES:
1. Questions must be different from the current query
2. Questions should be clear and specific
3. Focus on questions that can be answered with SQL queries on this flight data
4. Questions should be natural, conversational, and not too technical
5. Questions should logically follow from the current query and results
6. Return ONLY a JSON array of strings with NO additional text
7. Each question should be 2-15 words long

Return a JSON array in exactly this format:
["Question 1?", "Question 2?", "Question 3?"]"""

        # Call the Claude model
        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=500,
                temperature=0.7,  # Higher temperature for more variety
                system="You are a data analyst. Generate ONLY a JSON array of follow-up questions with NO additional text.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            questions_text = response.content[0].text.strip()
            
            # Clean up the response to ensure it's a valid JSON array
            questions_text = questions_text.replace("```json", "").replace("```", "").strip()
            
            # Try to parse as JSON
            import json
            try:
                questions = json.loads(questions_text)
                # Ensure we have a list of strings
                if not isinstance(questions, list):
                    questions = ["What other aspects of NYC flights would you like to explore?",
                                "Can you show me trends in flight delays by month?",
                                "How do flight patterns vary between different airlines?"]
                
                # Ensure we have exactly 3 questions
                while len(questions) < 3:
                    questions.append(f"Would you like to explore more data about {columns[0]['name'] if columns else 'flights'}?")
                
                if len(questions) > 3:
                    questions = questions[:3]
                
                # Ensure questions end with question marks
                questions = [q if q.endswith("?") else f"{q}?" for q in questions]
                
                return {
                    "questions": questions,
                    "status": "success"
                }
                
            except json.JSONDecodeError:
                # If JSON parsing fails, extract questions manually
                if "[" in questions_text and "]" in questions_text:
                    questions_text = questions_text[questions_text.find("["):questions_text.rfind("]")+1]
                    try:
                        questions = json.loads(questions_text)
                        if isinstance(questions, list) and len(questions) > 0:
                            # Ensure we have exactly 3 questions
                            while len(questions) < 3:
                                questions.append(f"Would you like to explore more data about {columns[0]['name'] if columns else 'flights'}?")
                            
                            if len(questions) > 3:
                                questions = questions[:3]
                            
                            # Ensure questions end with question marks
                            questions = [q if q.endswith("?") else f"{q}?" for q in questions]
                            
                            return {
                                "questions": questions,
                                "status": "success"
                            }
                    except:
                        pass
                
                # Fallback questions if JSON parsing fails
                return {
                    "questions": [
                        "What other aspects of NYC flights would you like to explore?",
                        "Can you show me trends in flight delays by month?",
                        "How do flight patterns vary between different airlines?"
                    ],
                    "status": "fallback",
                    "error": "Failed to parse questions as JSON"
                }
            
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {str(e)}")
            
            # Fallback questions if an error occurs
            return {
                "questions": [
                    "What other aspects of NYC flights would you like to explore?",
                    "Can you show me trends in flight delays by month?",
                    "How do flight patterns vary between different airlines?"
                ],
                "status": "fallback",
                "error": str(e)
            } 