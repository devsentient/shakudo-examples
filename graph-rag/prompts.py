from langchain.prompts import PromptTemplate

QWEN2_PROMPT_TEMPLATE = """
<|im_start|>system
You are a financial assistant who knows to read and understand the financial reports of a company.
You help with answering question from the user.
Please only answer the actual question, don't say anything else.
REMEMBER not to keep the acronyms intact. don't try to resolve it.

From the provided document, there might be a table with markdown format as in:

| Column 1 | Column 2 |
| Value 1 | Value 2 |

The answer will include 2 parts: the wanted value and the page number that contains that value.
If you can't find any relevant answer, please return <missing>

<|im_end|>
<|im_start|>user
From the following document:
{document}

Give me answer for this question {question}

NOTE that: 
1. If there are several mention of the same terms, please cite every mention in the document.
2. Must not omit page number in the answer.
3. The answer must be coherent and natural to human writing style
<|im_end|>
<|im_start|> assistant
"""

PROMPT_QWEN = PromptTemplate(template=QWEN2_PROMPT_TEMPLATE, 
                             input_variables=['document', 'question'])


QWEN2_QUESTION_TEMPLATE = """
<|im_start|>system
You are a financial assistant who knows to read and understand the financial reports of a company.
You will help to generate questions that can be answered with the infomation in the text chunk.
There are some guidelines:
1. The question has to be from short to middle length, which reflects how people normally ask for information.
2. The question has to mention document name in a natural way so that we could differentiate between different documents, 
but please not quote a full document name, since it doesn't sound natural anymore. 
And if the question has month information, it has to include year as well
    E.g: from QuarterlyActivitiesJun2023, you can ask "in the quarter of June 2023"
3. Please prioritize questions that ask for financial numbers.
4. Please do not generate yes/no question.
5. Always generate for 10 questions

From the provided document, there might be a table with markdown format as in:

| Column 1 | Column 2 |
| Value 1 | Value 2 |

Please generate each question in a new line.
<|im_end|>
<|im_start|>user
This is the document name: {name}
From the text chunk:
{document}


Please generate the questions.

<|im_end|>
<|im_start|> assistant
"""

PROMPT_QUESTION = PromptTemplate(template=QWEN2_QUESTION_TEMPLATE, 
                             input_variables=['document', 'name'])