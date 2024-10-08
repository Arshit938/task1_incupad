from django.shortcuts import render
from django.http.response import JsonResponse
import re
from django.conf import settings
from .models import docTable,formLabels
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
from fpdf import FPDF
import json
from django.views.decorators.csrf import csrf_exempt

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
        r'\bcreate\b.*\b(doc|pdf)\b',  
        r'\bwrite\b.*\bdocument\b',   
        r'\bwrite\b.*\b(doc|pdf)\b',   
        r'\bgenerate\b.*\bdocument\b',
        r'\bgenerate\b.*\b(doc|pdf)\b',
        r'\bnew\b.*\b(document|doc|pdf)\b',     
        r'\bstart\b.*\b(report|file|document|doc|pdf)\b',  
        r'\bdraft\b.*\b(letter|document|doc|pdf)\b',  
        r'\bbuild\b.*\breport\b',  
        r'\bcreate\b.*\bfile\b',   
        r'\bcompose\b.*\b(document|doc|pdf)\b',  
        r'\bopen\b.*\btemplate\b',  
        r'\bcreate\b.*\baffidavit\b',  
        r'\bprepare\b.*\baffidavit\b', 
        r'\bdraft\b.*\baffidavit\b',   
        r'\baffidavit\b.*\bform\b',
        r'\bfill\b.*\b(report|file|document|form|pdf)\b',    
    ]

    ans=any(re.search(pattern, text) for pattern in create_document_patterns)
    return ans

def getResponse(text):
    # for conversation
    llm=get_llm()
    response=llm(text)
    return response

@csrf_exempt
def processChat(request): # main function for chat endpoint
    '''
    output:
    {message : [{'id':document_id, 'path': document_path}......]
    '''
    try:
        if request.method == 'GET':
            data=json.loads(request.body)
            query=data.get('message')
        elif request.method == 'POST':
            data=json.loads(request.body)
            query=data.get('message')
        else: 
            return JsonResponse({'message' : []})
        print(query)
        category=categorizeText(query)
        if category:
            lst=docTable.objects.all()
            resp=[{'id':i.id,'path':i.doc_file.path} for i in lst]
        else:
            resp=getResponse(text=query)
        return JsonResponse({'message':resp})
    except Exception as e:
        return JsonResponse({'message':f'Error : {e}'})
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
    you are a text analyser and you are given a text which is an affidavit form and you have to find out all the fields that have spaces to be filled in that form in **output should have only field names seperated by ',' and should not have any extra messages from your side**
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
    res=output.split(',')
    return res

@csrf_exempt
def submitButton(request): # main function for submitbutton endpoint
    '''
    output format: JSON
    {'doc_id': doc_id, 'message':list_of_labels}
    '''
    try:
        if request.method == 'GET':
            data=json.loads(request.body)
            doc_id=data.get('doc_id')
        elif request.method == 'POST':
            data=json.loads(request.body)
            doc_id=data.get('doc_id')
        else: 
            print('invalidRequestMethod')
            return JsonResponse({'doc_id':doc_id,'message' : []})
        temp=docTable.objects.get(id=doc_id)
        if temp==None:
            #check if doc is present in the database
            return JsonResponse({'doc_id':doc_id,'message':'invaliDocumentId'})
        # checking if the document fields were fetched in past
        f=formLabels.objects.get(id=doc_id)
        if len(f.doc_fields)==0:
            data_info=extractData(file_path=temp.doc_file.path)
            field_info=extractFields(text=data_info)
            res={i:"" for i in field_info}
            f.doc_fields=res
            f.save() #saving fields for future use
        else:
            field_info=list(f.doc_fields.keys())
        return JsonResponse({'doc_id':doc_id,'message':field_info})
    except Exception as e:
        print(e)
        return JsonResponse({'doc_id':doc_id,'message':[]})

# api 3 submitform

def fillData(doc_id,data):
    llm=get_llm()
    obj=docTable.objects.get(id=doc_id)
    text_form=extractData(file_path=obj.doc_file.path)
    text_form=text_form.replace('GENERAL AFFIDAVIT','')
    pp2 = """
    {user_input}
    Using the above information, carefully fill in all the fields of the form provided below. 
    Ensure that the output retains the **exact line structure and formatting** as shown in the form template. 
    Do **not** change the alignment, spacing, or line breaks in the text. 

    Replace the placeholders with the appropriate information provided. 
    Replace '(Insert Statement)' with the Statement in above information. Leave the signature and date sections intact.

    Here is the form template to fill:

    {text_form}

    The filled form should be in the **same format** as above. The output should only contain the filled form with the **same line and paragraph breaks**  as in the original.
    **output should have only the filled form and should not have any extra messages**
"""
    # pp2="""
    # {user_input}
    # use the above information to fill all the fields of form given below
    # {text_form}
    # please return the above text_form after filling all the spaces with the given information
    # """
    prompt2=PromptTemplate(
        input_variables=['user_input','text_form'],
        template=pp2,
    )
    ip2=prompt2.format(user_input=data,text_form=text_form)
    ans=llm(ip2)
    return ans



def align_text_to_pdf(text,output_pdf,line_length=80):
    # Initialize PDF object
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    border_thickness = 0.75  # 0.75 corresponds to approximately 3-4 px
    pdf.set_line_width(border_thickness)
    pdf.rect(10, 10, pdf.w - 20, pdf.h - 20)

    pdf.set_font("Arial", "B", size=22)  # Bold font for heading
    pdf.cell(0, 20, "GENERAL AFFIDAVIT", ln=True, align="C")  # ln=True moves the cursor to next line after cell
    pdf.set_font("Arial", size=12)
    pdf.ln(15)
    output_str = ""
    lines = text.split('\n')
    # print(lines)
    line = ''
    # aligning text
    for i in lines:
        i=i.strip()
        if len(i) == 0:  
            if len(line) != 0:
                pdf.multi_cell(0, 10, line)  
                line = ''
            pdf.ln(10)  
            continue

        words = i.split(' ')
        if len(i) <= line_length // 2:  
            if len(line) != 0:
                pdf.multi_cell(0, 10, line)
                line = ''
                pdf.ln(10)  
            pdf.multi_cell(0, 10, i)
            continue

        for j in words:
            temp = line + j + ' '
            if len(temp) < line_length:
                line = temp
            else:
                pdf.multi_cell(0, 10, line) 
                line = j + ' '  

    # If any text is left in the line, add it to the PDF
    if line:
        pdf.multi_cell(0, 10, line)
    # Save the PDF to the specified file
    pdf.output(output_pdf)
    print(f"PDF saved as {output_pdf}")

@csrf_exempt
def submitForm(request): #main function for submitform endpoint
    try:
        if request.method == 'GET':
            data=json.loads(request.body)
            doc_id=data.get('doc_id')
            user_ip=data.get('user_input')
        elif request.method == 'POST':
            data=json.loads(request.body)
            doc_id=data.get('doc_id')
            user_ip=data.get('user_input')
        else: 
            return JsonResponse({'file':'','message' : 'invalidRequestMethod'})
        #fetching the fields to be filled in document
        # obj=docTable.objects.get(id=doc_id)
        f=formLabels.objects.get(id=doc_id)
        lst=list(f.doc_fields.keys())
        # filling the values of fields in dict acc to user_input
        for i in range(len(user_ip)):
            f.doc_fields[lst[i]]=user_ip[i]
        filled_text=fillData(doc_id=doc_id,data=f.doc_fields)#using llm to fill data
        pdf_file_path = os.path.join(filled_pdfs_path,f'filled_file_{doc_id}.pdf')
        align_text_to_pdf(text=filled_text,output_pdf=pdf_file_path)
        return JsonResponse({'message':str(pdf_file_path)})

    except Exception as e:
        return JsonResponse({'message':e})
