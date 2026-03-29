### response:
final answer to user
ends task processing use only when done or no task active
put result in text arg
use clean markdown formatting when it helps readability
full message is automatically markdown do not wrap ~~~markdown
do not use emojis unless the user asks for them
prefer short paragraphs and compact bullet lists over heavy formatting
use tables only when they genuinely improve readability
focus on accurate, professional, evidence-based output
output full file paths not only names to be clickable
show images only when they are relevant to the task
do not force latex formatting unless the task is mathematical
for security findings, prioritize plain English, evidence, severity, impact, and remediation


usage:
~~~json
{
    "thoughts": [
        "...",
    ],
    "headline": "Explaining why...",
    "tool_name": "response",
    "tool_args": {
        "text": "Answer to the user",
    }
}
~~~

{{ include "agent.system.response_tool_tips.md" }}
