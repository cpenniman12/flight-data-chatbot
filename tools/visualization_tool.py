"""
Visualization Tool

This module implements a tool that generates visualization code for data.
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd

import anthropic

from tools.base_tool import BaseTool, ToolParameter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class VisualizationTool(BaseTool):
    """Tool for generating visualization code for data."""

    def __init__(self, client: anthropic.Anthropic):
        """
        Initialize the VisualizationTool.
        
        Args:
            client: The Anthropic client
        """
        super().__init__(
            name="generate_visualization",
            description="Generates visualization code for data using Plotly Express",
            parameters=[
                ToolParameter(
                    name="results",
                    description="The query results to visualize",
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
                    name="query",
                    description="The user query that generated the data",
                    param_type="string",
                    required=True
                )
            ]
        )
        self.client = client
        
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the visualization tool.
        
        Args:
            **kwargs: The parameters for the tool
                - results: The query results to visualize
                - columns: The column metadata for the results
                - query: The user query that generated the data
                
        Returns:
            A dictionary with the visualization code
        """
        # Validate parameters
        params = self.validate_parameters(kwargs)
        results = params["results"]
        columns = params["columns"]
        user_query = params["query"]
        
        # Check if we have results to visualize
        if not results:
            return {
                "error": "No data to visualize",
                "status": "error"
            }
        
        # Convert results back to DataFrame for analysis
        df = pd.DataFrame(results)
        
        # Determine column types (numeric vs categorical)
        sample_data_description = {}
        column_types = {}
        
        # Limit sample size to avoid context overflow
        sample_size = min(5, len(df))
        sample_df = df.head(sample_size)
        
        for col in df.columns:
            try:
                if pd.api.types.is_numeric_dtype(df[col]):
                    column_types[col] = "numeric"
                    # Calculate stats for numeric columns
                    sample_data_description[col] = {
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "mean": float(df[col].mean()),
                        "type": "numeric"
                    }
                else:
                    column_types[col] = "categorical"
                    # Get unique values for categorical columns
                    unique_values = df[col].nunique()
                    sample_data_description[col] = {
                        "unique_values": min(unique_values, 10),
                        "type": "categorical"
                    }
            except Exception as e:
                logger.warning(f"Error analyzing column {col}: {str(e)}")
                column_types[col] = "unknown"
                sample_data_description[col] = {"type": "unknown"}
        
        # Create a data sample for the prompt
        data_sample = sample_df.to_dict(orient="records")
        
        # Create the prompt
        prompt = f"""Generate visualization code using Plotly Express for the following data:

Column Information:
{str(sample_data_description)}

Data Sample (first {sample_size} rows):
{str(data_sample)}

User Query: "{user_query}"

Please generate Python code that creates an appropriate visualization for this data using Plotly Express.
The visualization should help answer the user's query effectively.

Valid chart types include:
- Line charts (px.line)
- Bar charts (px.bar)
- Scatter plots (px.scatter)
- Histograms (px.histogram)
- Box plots (px.box)
- Pie charts (px.pie)
- Heatmaps (px.imshow)

IMPORTANT RULES:
1. The code should ONLY use Plotly Express (px)
2. Return ONLY the Python code with no explanations or markdown
3. The code must be executable as-is
4. Make all imports explicit (import plotly.express as px)
5. Avoid complex code with conditionals or functions
6. Ensure axis labels and title are descriptive
7. Use color-blind friendly color schemes when possible
8. Choose the chart type that best represents the data and answers the query
9. No figure.show() in the code

Use this template:
```python
import plotly.express as px

# Your visualization code here
fig = px.chart_type(...)

# Update layout as needed
fig.update_layout(
    title="Descriptive title",
    xaxis_title="X Axis Label",
    yaxis_title="Y Axis Label"
)
```

Return ONLY the executable visualization code."""

        # Call the Claude model
        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1500,
                temperature=0,
                system="You are a data visualization expert. Generate ONLY Python code using Plotly Express with no explanations or markdown.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            viz_code = response.content[0].text.strip()
            
            # Clean up the code - remove markdown if present
            if viz_code.startswith("```python"):
                viz_code = viz_code.split("```python", 1)[1]
            if viz_code.startswith("```"):
                viz_code = viz_code.split("```", 1)[1]
            if viz_code.endswith("```"):
                viz_code = viz_code.rsplit("```", 1)[0]
            
            viz_code = viz_code.strip()
            
            # Check if the code is too complex or potentially problematic
            if len(viz_code.split("\n")) > 30 or "def " in viz_code or "class " in viz_code:
                # Generate a simpler visualization as fallback
                fallback_prompt = f"""Generate a SIMPLE visualization using Plotly Express for the data with columns: {list(df.columns)}.
                
Choose ONE chart type based on the user query: "{user_query}"

Return ONLY executable Python code - no explanations or markdown.
Keep it under 15 lines of code."""

                fallback_response = self.client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=1000,
                    temperature=0,
                    system="You are a data visualization expert. Generate ONLY simple Python code using Plotly Express with no explanations.",
                    messages=[{"role": "user", "content": fallback_prompt}]
                )
                
                viz_code = fallback_response.content[0].text.strip()
                
                # Clean up the code again
                if viz_code.startswith("```python"):
                    viz_code = viz_code.split("```python", 1)[1]
                if viz_code.startswith("```"):
                    viz_code = viz_code.split("```", 1)[1]
                if viz_code.endswith("```"):
                    viz_code = viz_code.rsplit("```", 1)[0]
                
                viz_code = viz_code.strip()
            
            # Ensure required imports are present
            if "import plotly.express as px" not in viz_code:
                viz_code = "import plotly.express as px\n" + viz_code
            
            # Ensure there's no figure.show() call
            viz_code = viz_code.replace("fig.show()", "")
            
            return {
                "visualization_code": viz_code,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error generating visualization code: {str(e)}")
            
            # Generate a very simple fallback visualization
            simple_fallback = """import plotly.express as px

# Create a simple visualization based on the data
fig = px.bar(df)

# Update layout
fig.update_layout(
    title="Data Visualization",
    xaxis_title="X Axis",
    yaxis_title="Value"
)"""
            
            return {
                "visualization_code": simple_fallback,
                "error": f"Error in primary visualization generation: {str(e)}",
                "status": "fallback"
            } 