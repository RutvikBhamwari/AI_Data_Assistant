import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello Claude! I am learning to build AI apps. Say hello back and wish me luck!"}
    ]
)

print(message.content[0].text)