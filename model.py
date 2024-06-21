import streamlit as st
import pandas as pd
import spacy
import pytesseract
from PIL import Image
import json
from pymongo import MongoClient
from bson import ObjectId

# Load the spaCy model
nlp = spacy.load("en_core_web_sm")

def preprocess_structured_data(structured_data):
    df = pd.DataFrame(structured_data)
    return df

def preprocess_text_data(text_data):
    doc = nlp(text_data)
    processed_text = ' '.join([token.lemma_ for token in doc if not token.is_stop and token.is_alpha])
    return processed_text

def preprocess_image_data(image_path):
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    processed_text = preprocess_text_data(text)
    return processed_text

def parse_data_model_specification(specification):
    data_model_spec = json.loads(specification)
    return data_model_spec

def format_medications(medications):
    med_list = []
    for med in medications:
        end_date = med.get('end_date', 'ongoing')
        start_date = med.get('start_date', 'Unknown')  # Handle missing start_date
        med_list.append(f"{med['name']} (Dosage: {med['dosage']}, Start Date: {start_date}, End Date: {end_date})")
    return "The patient is currently on the following medications: " + ", ".join(med_list) + "."


def format_disease_states(disease_states):
    state_list = []
    for state in disease_states:
        end_date = state.get('endDate', 'present')
        state_list.append(f"{state['state']} (from {state['startDate']} to {end_date})")
    return "The patient's disease states are: " + ", ".join(state_list) + "."

def format_comorbidities(comorbidities):
    return "The patient has the following comorbidities: " + ", ".join(comorbidities) + "."

def generate_prompts(data_model_spec, patient_data):
    prompts = []
    for element in data_model_spec['required_information']:
        prompt_text = element['prompt']
        answer = 'Unknown'
        if element['source'] == 'procedures':
            answer = next((item['date'] for item in patient_data.get('procedures', []) if item['type'] == element['name']), 'Unknown')
        elif element['source'] == 'labResults':
            answer = next((item['value'] for item in patient_data.get('labResults', []) if item['test'] == element['name']), 'Unknown')
        elif element['source'] == 'imagingStudies':
            answer = next((item['findings'] for item in patient_data.get('imagingStudies', []) if item['type'] == element['name']), 'Unknown')
        elif element['source'] == 'medications':
            answer = format_medications(patient_data.get('medications', []))
        elif element['source'] == 'comorbidities':
            answer = format_comorbidities(patient_data.get('comorbidities', []))
        elif element['source'] == 'diseaseStates':
            answer = format_disease_states(patient_data.get('diseaseStates', []))
        elif element['source'] == 'chemotherapy':
            # Find the latest chemotherapy date
            chemotherapy_dates = [item['date'] for item in patient_data.get('procedures', []) if item['type'] == 'Chemotherapy']
            answer = max(chemotherapy_dates) if chemotherapy_dates else 'Unknown'
        else:
            answer = patient_data.get(element['name'], 'Unknown')
        prompts.append({"prompt": prompt_text, "answer": answer})
    return prompts

def evaluate_prompts(prompts, generated_answers):
    true_answers = {p['prompt']: str(p['answer']).strip() for p in prompts}  # Convert to string and strip
    pred_answers = {a['prompt']: str(a['answer']).strip() for a in generated_answers}  # Convert to string and strip
    
    correct = sum(1 for k in true_answers if k in pred_answers and true_answers[k].lower() == pred_answers[k].lower())
    accuracy = correct / len(true_answers)
    return accuracy
    
    correct = sum(1 for k in true_answers if k in pred_answers and true_answers[k].strip().lower() == pred_answers[k].strip().lower())
    accuracy = correct / len(true_answers)
    return accuracy

# Streamlit UI
st.title("LLM Prompt Generation for Oncology Data")

# MongoDB connection
client = MongoClient("mongodb+srv://pratappawar:onco321@oncocare.nrq4szv.mongodb.net")
db = client["OncoCare_Final_DB"]
collection = db["patients"]

# Hardcoded data model specification with more prompts
data_model_specification = '''
{
    "required_information": [
        {
            "prompt": "When was the Radical Prostatectomy performed?",
            "name": "Radical Prostatectomy",
            "source": "procedures"
        },
        {
            "prompt": "What was the last PSA level?",
            "name": "PSA",
            "source": "labResults"
        },
        {
            "prompt": "What medications is the patient currently on?",
            "name": "medications",
            "source": "medications"
        },
        {
            "prompt": "What is the patient's diagnosis date?",
            "name": "diagnosisDate",
            "source": "general"
        }
    ]
}
'''



# MongoDB connection
client = MongoClient("mongodb+srv://pratappawar:onco321@oncocare.nrq4szv.mongodb.net")
db = client["OncoCare_Final_DB"]
collection = db["patients"]

# Input field for patient ID
patient_id = st.text_input("Enter Patient ID")

if patient_id:
    # Fetch patient data from MongoDB
    patient_data = collection.find_one({"_id": ObjectId(patient_id)})

    if patient_data:
        st.write("Patient Data:")
        st.json(patient_data)

        # Parse data model specification
        data_model_spec = parse_data_model_specification(data_model_specification)

        # Generate prompts
        prompts = generate_prompts(data_model_spec, patient_data["patientDetails"])

        st.write("Generated Prompts:")
        st.json(prompts)

        # Display prompts in text boxes
        prompt_texts = "\n".join([f"{p['prompt']} - {p['answer']}" for p in prompts])
        st.text_area("Generated Prompts", prompt_texts, height=200)

        # Copy to clipboard button
        if st.button("Copy Prompts to Clipboard"):
            st.write("Prompts copied to clipboard.")
            st.code(prompt_texts, language="text")

        # Mock generated answers for demonstration
        generated_answers = [
            {"prompt": "When was the last chemotherapy performed?", "answer": "2023-02-01"},
            {"prompt": "What are the findings of the most recent CT Scan?", "answer": "No evidence of metastatic disease"},
            {"prompt": "What was the last PSA level?", "answer": "8.2"},
             {"prompt": "What is the patient's diagnosis date?", "answer": "2020-01-01"}
        ]

        # Evaluate prompts
        accuracy = evaluate_prompts(prompts, generated_answers)
        #st.write(f"Accuracy: {accuracy * 100:.2f}%")

        st.write("Sample Generated Answers:")
        st.json(generated_answers)

    else:
        st.write("Patient ID not found in the database.")

else:
    st.write("Please enter a valid Patient ID.")


# In[ ]:





# In[ ]:




