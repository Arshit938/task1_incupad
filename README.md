# task 1

# API input and outputs:
## API 1:
endpoint name: 'chat'
input : {'message':query}
output : {'message' : list_of_docs/chat_reply/error}

## API 2:
endpoint name : 'submitbutton'
input : {'doc_id':document_id}
output format: {'doc_id': doc_id, 'message':list_of_labels}

## API 3:
endpoint name: 'submitform'
input : {'doc_id':document_id,'user_input':list_of_answers_to_the_fields}
output : {'message' : path_to_pdf}
## Note:

1. Please read all the comments on functions; they state the format of the output generated by a function.

2. Please install all the Python libraries mentioned in `requirements.txt`.

3. There is a text file `superuserCredentials.txt` which contains the ID and password for the admin.

4. Use your own secret key for Cohere. Follow the URL: [https://cohere.com/chat](https://cohere.com/chat) to get your API key.

5. Place your API key in `settings.py`. You will find a comment for it at the end of the file. Fill your API key there.
