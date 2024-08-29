from django.shortcuts import render
from django.http.response import JsonResponse
import re
from django.conf import settings
from .models import docTable,newPdfUpload
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextBox, LTTextLine, LAParams
import os
from langchain import Cohere, LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import Cohere as CohereLLM
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import units
from reportlab.lib.utils import simpleSplit


# setting up llms secret key as os enviornment variable

def get_llm():
    os.environ['COHERE_API_KEY'] = settings.COHERE_API_KEY #please enter your api key in settings.py file for safety of key
    return Cohere()

#to upload filled pdfs
filled_pdfs_path = os.path.join(settings.MEDIA_ROOT, 'filled_pdfs')
os.makedirs(filled_pdfs_path, exist_ok=True)

# api1 chat

def categorizeText(text):
    # Output : returns True when user requires document creation
    text=text.lower()
    create_document_patterns = [
        r'\bcreate\b.*\bdocument\b',  
        r'\bwrite\b.*\bdocument\b',   
        r'\bgenerate\b.*\bdocument\b',
        r'\bnew\b.*\bdocument\b',     
        r'\bstart\b.*\b(report|file|document)\b',  
        r'\bdraft\b.*\b(letter|document)\b',  
        r'\bbuild\b.*\breport\b',  
        r'\bcreate\b.*\bfile\b',   
        r'\bcompose\b.*\bdocument\b',  
        r'\bopen\b.*\btemplate\b',  
        r'\bcreate\b.*\baffidavit\b',  
        r'\bprepare\b.*\baffidavit\b', 
        r'\bdraft\b.*\baffidavit\b',   
        r'\baffidavit\b.*\bform\b',    
    ]

    ans=any(re.search(pattern, text) for pattern in create_document_patterns)
    return ans

def getResponse(text):
    # for conversation
    llm=get_llm()
    response=llm(text)
    return response

def processChat(request): # main function for chat endpoint
    '''
    output:
    if category is document_creation then message will be "success" and doc_array will be a list of json's of format [{'id' : id ,'path' : doc_file_url},.....]
    if category is conversation then message will be response to the conversation and doc_array field will be None
    '''
    try:
        if request.method == 'GET':
            query=request.GET.get('message')
        elif request.method == 'POST':
            query=request.POST.get('message')
        else: 
            return JsonResponse({'message' : []})
        category=categorizeText(query)
        if category:
            lst=docTable.objects.all()
            resp=[{'id':i.id,'path':i.doc_file.url} for i in lst]
        else:
            resp=getResponse(text=query)
        return JsonResponse({'message':resp})
    except Exception as e:
        return JsonResponse({'message':f'Error : {e}','doc_array':[],'category':'Error'})
# api2 submitbutton
    
def extractData(file_path):
    try:
        text = ''
        laparams = LAParams()

        for page_layout in extract_pages(file_path, laparams=laparams):
            for element in page_layout:
                if isinstance(element, LTTextBox):
                    for text_line in element:
                        if isinstance(text_line, LTTextLine):
                            text += text_line.get_text()
        return text
    except Exception as e:
        print(e)
        return ''
    
def split_str(s):
    x=s.split('\n')
    for i in x:
        if ',' in i:
            res=i.split(',')
    return res
def extractFields(text):
    '''
    output format: [label1, label2.....]
    '''
    prompt_template="""
    you are a text analyser and you are given a text which is an affidavit form and you have to find out all the fields that are to be filled in that form in output only give the field names separated by comma below is the form in text format
    {text_form}
    """
    llm=get_llm()
    prompt = PromptTemplate(
        input_variables=["text_form"],
        template=prompt_template
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    text_form = text
    output = chain.run(text_form=text_form)
    res=split_str(output)
    return res

def submitButton(request): # main function for submitbutton endpoint
    '''
    output format: JSON
    {'doc_id': doc_id, 'message':list_of_labels}
    '''
    try:
        if request.method == 'GET':
            doc_id=request.GET.get('doc_id')
        elif request.method == 'POST':
            doc_id=request.POST.get('doc_id')
        else: 
            print('invalidRequestMethod')
            return JsonResponse({'doc_id':doc_id,'message' : []})
        temp=docTable.objects.get(id=doc_id)
        if len(temp)==0:
            #check if doc is present in the database
            return JsonResponse({'doc_id':doc_id,'message':'invaliDocumentId'})
        # checking if the document fields were fetched in past
        if len(temp.doc_fields)==0:
            data_info=extractData(file_path=temp.doc_file.url)
            field_info=extractFields(text=data_info)
            res={i:"" for i in field_info}
            temp.doc_fields=res
            temp.save() #saving fields for future use
        else:
            field_info=list(temp.doc_fields.keys())
        return JsonResponse({'doc_id':doc_id,'message':field_info})
    except Exception as e:
        print(e)
        return JsonResponse({'doc_id':doc_id,'message':[]})

# api 3 submitform

def fillData(doc_id,data):
    llm=get_llm()
    obj=docTable.objects.get(id=doc_id)
    text_form=extractData(obj.doc_file.url)
    pp2="""
    {user_input}
    use the above information to fill all the fields of form given below
    {text_form}
    output sting should only contain filled form and also replace the (Insert Statement) with the statement provided and leave the signature section as it is in the information preserve structure of form
    """
    prompt2=PromptTemplate(
        input_variables=['user_input','text_form'],
        template=pp2,
    )
    ip2=prompt2.format(user_input=data,text_form=text_form)
    ans=llm(ip2)
    return ans



def create_pdf(text, filename):
    page_width, page_height = A4
    left_margin = right_margin = 1 * units.inch  # 1 inch margins
    top_margin = bottom_margin = 1 * units.inch

    usable_width = page_width - left_margin - right_margin
    usable_height = page_height - top_margin - bottom_margin

    c = canvas.Canvas(filename, pagesize=A4)
    c.setFont("Times-Roman", 12)

    lines = simpleSplit(text, "Times-Roman", 12, usable_width)

    y_position = page_height - top_margin


    for line in lines:
        if y_position <= bottom_margin:
            c.showPage()  # Start a new page
            c.setFont("Times-Roman", 12)
            y_position = page_height - top_margin  # Reset y position for new page

        # Draw text on the canvas
        c.drawString(left_margin, y_position, line)
        y_position -= 14  
    c.save()


def submitForm(request): #main function for submitform endpoint
    try:
        if request.method == 'GET':
            doc_id=request.GET.get('doc_id')
            user_ip=request.GET.get('user_input')
        elif request.method == 'POST':
            doc_id=request.POST.get('doc_id')
            user_ip=request.POST.get('user_input')
        else: 
            return JsonResponse({'file':'','message' : 'invalidRequestMethod'})
        #fetching the fields to be filled in document
        obj=docTable.objects.get(id=doc_id)
        lst=list(obj.doc_fields.keys())
        # filling the values of fields in dict acc tu user_input
        for i in range(len(user_ip)):
            obj.doc_fields[lst[i]]=user_ip[i]
        filled_text=fillData(doc_id=doc_id,data=obj.doc_fields)#using llm to fill data
        pdf_file_path = os.path.join(filled_pdfs_path,f'filled_file_{doc_id}.pdf')
        create_pdf(text=filled_text,filename=pdf_file_path)
        return JsonResponse({'message':pdf_file_path})

    except Exception as e:
        return JsonResponse({'message':e})