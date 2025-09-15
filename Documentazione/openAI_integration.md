We will use the brand new responses API from OpenAI

Set up:
from openai import OpenAI
import os
# Load API key from environment variable
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Our prompt ID (stored in .env as OPENAI_PROMPT_ID)
prompt_id = os.environ.get('OPENAI_PROMPT_ID')  # pmpt_68bee228e8288196811e9e0426855ad501793deee998d9b1

To initiate a conversation, we can use the following command:

conversation = client.conversations.create()

and get the conversation.id from the conversation object

Furthermore, we can initiate the conversation like this:

conversation = client.conversations.create(
  metadata={"topic": "demo"},
  items=[
    {"type": "message", "role": "user", "content": "Hello!"}
  ]
)

I don't think we will ever need the metadata parameter, but it could be useful to use the items parameter to jump start a conversation. 

How to generate a model response. We will use always the same prompt id, which is our guideline. The version number is optional, leave it out to use the default (you should asusme we want to use the default, if not i will tell you otherwise)

Please note that we can attach the conversation id. This will store the thread of messages as per explained by OpenAI: Items from this conversation are prepended to input_items for this response request. Input items and output items from this response are automatically added to this conversation after this response completes.

response = client.responses.create(
  prompt={
    "id": prompt_id,  # Uses the prompt ID from environment variable
    "version": "2"
  },
  input=[{ "role": "user", "content": "Hello friend" }],
  model="gpt-4.1",
  conversation=conversation.id
)

print(response.output_text)

Please be aware that for streaming, we can set a parameter stream=True. Given that we will be sending whatsapp messages, for now let's not use streaming. 
The response can be printed this way:
for event in response:
print(event)


Then, i can keep adding messages to the conversation as user, and everything will be stored inside the conversation. I can retrieve each response everytime, or get all items in a convo like this:

items = client.conversations.items.list(conv_id, limit=10)
print(items.data)

If needed, we can delete a conversation. 

deleted = client.conversations.delete("conv_123")
print(deleted)


We can analyze a piece of text and ask OpenAi to return a structured output

from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    is_male: Optional[bool] = None
    found_all_info : bool
    what_is_missing : Optional[str] = None

response = client.responses.parse(
    model="gpt-4o",
    input=[
        {"role": "system", "content": "Extract the client information. Name, age and a boolean to see if it's a male. If you found all info in the text, return true"},
        {
            "role": "user",
            "content": " i'm a male",
        },
    ],
    text_format=User,
)

user = response.output_parsed
user

the user would print like this: User(name='Mattia', age=28, is_male=True, found_all_info=True)

then we would upload the info to the conversation: 
items = client.conversations.items.create(
  conv_id,
  items=[
    {
      "type": "message",
      "role": "assistant",
      "content": [{"type": "output_text", "text": f"From our analysis, this is what is missing from the client:{user.model_dump_json()} "}],
    }
  ],
)
print(items.data)


USING VARIABLES

We can add variables in the system prompt, and when we create a response from the API we can set those values like this

response = client.responses.create(
  prompt={
    "id": 'pmpt_68c132ddf7c08196bba39f8e02a7028e0c7bdc9c964d1940',
    "variables": {
            "name": "Jane Doe",
            "age": "40"
        }
  },
  input=[{ "role": "user", "content": "Hello friend" }],
  model="gpt-4.1"
)

print(response.output_text)

please read this!!
Okay, I know this method works, but I think I have another idea. In the new section I just added in the setup guide @SETUP_GUIDE.md    I explained to you how we can pass variables to the prompt and make it a dynamic prompt. My idea is to eliminate all this stuff you explained to me that we couldn't do and just adjust my prompt to pass it the relevant information by the user. If info is still none, okay, so it's not provided by the client, we make the prompt understand and so the system that gracefully needs to ask for it. If a user provides info at the next prompt, we pass it as information. In the field where we pass the variables, we can do: if none, put the actual value; if none, put a string; please ask for this or instruct in the prompt how to deal with a none. The current status of my prompt is this: I still have to add variables. I will do it with your help. I would like you to analyze the situation, provide feedback, and tell me if it's a good plan. Like this, we can just let the AI take care of the asking part. When all the info is gotten, the assistant can take care of actually helping the user. Current prompt: Sei un agente Whatsapp incaricato all'assistenza clienti e all'acquisizione delle informazioni di base del contatto.