"""
LLM-powered search service using Anthropic Claude API.

This service sends user search queries to Claude, which can use
defined tools to query the database and return natural language responses.
"""

import json
import logging
import markdown
import bleach
import anthropic
from django.conf import settings
from . import search_tools

logger = logging.getLogger(__name__)

# Allowed HTML tags for sanitization
ALLOWED_TAGS = [
    'a', 'p', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'pre',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'blockquote'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'code': ['class']
}


def markdown_to_html(text):
    """
    Convert markdown text to sanitized HTML.

    Args:
        text: Markdown formatted text

    Returns:
        Safe HTML string
    """
    # Convert markdown to HTML
    html = markdown.markdown(
        text,
        extensions=['fenced_code', 'nl2br', 'tables']
    )

    # Sanitize HTML to prevent XSS
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )

    return clean_html


# Tool definitions in MCP-compatible format
SEARCH_TOOLS = [
    {
        "name": "search_assignments",
        "description": "Search for assignments (projects/opdrachten) by various criteria with pagination support. Returns up to 50 results per call. If total_count > returned_count, call again with offset=50, offset=100, etc. to get more results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search in assignment name, organization, or extra info"
                },
                "organization": {
                    "type": "string",
                    "description": "Filter by organization name"
                },
                "ministry": {
                    "type": "string",
                    "description": "Filter by ministry name or abbreviation"
                },
                "status": {
                    "type": "string",
                    "enum": ["LEAD", "VACATURE", "INGEVULD", "AFGEWEZEN"],
                    "description": "Filter by assignment status"
                },
                "offset": {
                    "type": "integer",
                    "description": "Starting position for pagination (default: 0). Use offset=50 for page 2, offset=100 for page 3, etc.",
                    "default": 0
                }
            }
        }
    },
    {
        "name": "search_colleagues",
        "description": "Search for colleagues (consultants/medewerkers) by name, email, skills, or brand with pagination support. Returns up to 50 results per call. If total_count > returned_count, call again with offset=50, offset=100, etc. to get more results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search in colleague name, email, skills, or expertises"
                },
                "skill": {
                    "type": "string",
                    "description": "Filter by skill name"
                },
                "brand": {
                    "type": "string",
                    "description": "Filter by brand name"
                },
                "offset": {
                    "type": "integer",
                    "description": "Starting position for pagination (default: 0). Use offset=50 for page 2, offset=100 for page 3, etc.",
                    "default": 0
                }
            }
        }
    },
    {
        "name": "search_ministries",
        "description": "Search for ministries by name or abbreviation with pagination support. Returns up to 50 results per call. If total_count > returned_count, call again with offset=50, offset=100, etc. to get more results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search in ministry name or abbreviation"
                },
                "offset": {
                    "type": "integer",
                    "description": "Starting position for pagination (default: 0). Use offset=50 for page 2, offset=100 for page 3, etc.",
                    "default": 0
                }
            }
        }
    },
    {
        "name": "get_assignment_details",
        "description": "Get detailed information about a specific assignment including its services and placements. Use this when you need full details about a particular assignment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignment_id": {
                    "type": "integer",
                    "description": "The ID of the assignment to retrieve"
                }
            },
            "required": ["assignment_id"]
        }
    },
    {
        "name": "get_colleague_details",
        "description": "Get detailed information about a specific colleague including their current placements. Use this when you need full details about a particular colleague.",
        "input_schema": {
            "type": "object",
            "properties": {
                "colleague_id": {
                    "type": "integer",
                    "description": "The ID of the colleague to retrieve"
                }
            },
            "required": ["colleague_id"]
        }
    }
]


def execute_tool(tool_name, tool_input):
    """
    Execute a tool by routing to the appropriate search_tools function.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Dictionary of input parameters

    Returns:
        Tool execution result
    """
    tool_map = {
        'search_assignments': search_tools.search_assignments,
        'search_colleagues': search_tools.search_colleagues,
        'search_ministries': search_tools.search_ministries,
        'get_assignment_details': search_tools.get_assignment_details,
        'get_colleague_details': search_tools.get_colleague_details,
    }

    tool_func = tool_map.get(tool_name)
    if not tool_func:
        return {'error': f'Unknown tool: {tool_name}'}

    try:
        return tool_func(**tool_input)
    except Exception as e:
        return {'error': f'Tool execution failed: {str(e)}'}


def process_search_query(search_query):
    """
    Process a natural language search query using Claude with tool use.

    Args:
        search_query: Natural language search query from user

    Returns:
        Dictionary with:
            - success: Boolean indicating success
            - response: Natural language response from Claude (if successful)
            - user_message: User-facing error message (if failed)
    """
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        logger.warning('LLM search attempted but ANTHROPIC_API_KEY is not configured')
        return {
            'success': False,
            'response': None,
            'user_message': 'LLM-aangedreven zoeken is momenteel niet beschikbaar'
        }

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # System prompt to guide Claude's behavior
        system_prompt = """Je bent een zoekassistent voor een consultancy organisatie.
Je helpt gebruikers met het zoeken naar opdrachten (assignments), collega's (colleagues), en ministeries.

Wanneer een gebruiker een zoekopdracht geeft:
1. Gebruik de beschikbare tools om relevante informatie op te halen
2. Geef een helder, beknopt antwoord in het Nederlands
3. Vermeld specifieke details zoals namen, organisaties, en data
4. Als je meerdere resultaten vindt, geef dan een samenvatting van de belangrijkste
5. Als je specifieke opdrachten / collega's of plaatsingen geeft, maak deze dan klikbaar met een URL.

Blijf vriendelijk en professioneel."""

        messages = [
            {
                "role": "user",
                "content": search_query
            }
        ]

        tool_results = []
        max_iterations = 5  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Call Claude with tools
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                system=system_prompt,
                tools=SEARCH_TOOLS,
                messages=messages
            )

            # Check if Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Extract tool uses and execute them
                tool_use_blocks = [block for block in response.content if block.type == "tool_use"]

                # Add assistant's response to messages
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Execute each tool and collect results
                tool_result_contents = []
                for tool_use in tool_use_blocks:
                    tool_name = tool_use.name
                    tool_input = tool_use.input

                    # Execute the tool
                    result = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        'tool': tool_name,
                        'input': tool_input,
                        'result': result
                    })

                    # Add tool result to messages
                    tool_result_contents.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })

                # Add tool results to messages
                messages.append({
                    "role": "user",
                    "content": tool_result_contents
                })

            elif response.stop_reason == "end_turn":
                # Claude is done, extract final response
                text_blocks = [block.text for block in response.content if hasattr(block, 'text')]
                final_response = '\n'.join(text_blocks)

                # Convert markdown to HTML
                html_response = markdown_to_html(final_response)

                return {
                    'success': True,
                    'response': html_response
                }

            else:
                # Unexpected stop reason
                logger.error(f'LLM search unexpected stop reason: {response.stop_reason}')
                return {
                    'success': False,
                    'response': None,
                    'user_message': 'LLM-aangedreven zoeken is tijdelijk niet beschikbaar'
                }

        # Max iterations reached
        logger.error(f'LLM search max iterations reached for query: {search_query}')
        return {
            'success': False,
            'response': None,
            'user_message': 'LLM-aangedreven zoeken is tijdelijk niet beschikbaar'
        }

    except anthropic.APIError as e:
        logger.error(f'Anthropic API error during LLM search: {str(e)}', exc_info=True)
        return {
            'success': False,
            'response': None,
            'user_message': 'LLM-aangedreven zoeken is tijdelijk niet beschikbaar'
        }
    except Exception as e:
        logger.error(f'Unexpected error during LLM search: {str(e)}', exc_info=True)
        return {
            'success': False,
            'response': None,
            'user_message': 'LLM-aangedreven zoeken is tijdelijk niet beschikbaar'
        }
