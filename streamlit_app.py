import streamlit as st
from openai import OpenAI

PROMPT = """
Generate a SQL query using the schema provided below.

If the requested information isn't available in the schema, avoid generating queries with placeholder or dummy tables. Instead, let the user know that you don't have enough schema details to provide an answer and ask them to share more information about the relevant schema or tables where the data might be found.

-- nlp_api_history table contains entry for every patient query that was sent to the NLP
CREATE TABLE public.nlp_api_history (
    request_id character varying(18) NOT NULL,
    automated_interaction_id character varying(18), -- input question id
    user_id character varying(18), -- patient id
    question text NOT NULL, -- patient's query
    answer text NOT NULL, -- answer generated by NLP
    topic character varying(256),
    api_type integer NOT NULL,
    "references" text,
    exceptions text,
    confidence double precision,
    elapsed_time integer,
    version character varying(18),
    translated_query text,
    intent public.intent,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);

-- nlp_rd_feedback stores the feedback given by RD(Registered Dietitions).
CREATE TABLE public.nlp_rd_feedback (
    id character varying(18) NOT NULL,
    automated_interaction_id character varying(18) NOT NULL, -- The answer that was provided by RD to the patient
    edited_by character varying(255) NOT NULL, -- the email of the RD who gave the feedback
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    category character varying(255) NOT NULL, -- category of feedback
    subcategory character varying(255), -- subcategory of feedback
    other text -- if they selected category of "other" or subcategory of "other" then this field would contain the freetext comment by them
);

-- user_opt_actions stores the patients who have opted out of INA. 
CREATE TABLE public.user_opt_actions (
    id character varying(18) NOT NULL,
    contact_id character varying(18) NOT NULL,
    opt_type public.opttype NOT NULL, -- whether it's opt out or opt in
    opt_origin public.optorigin NOT NULL,
    comment character varying(255), -- when RD manually opt outs user then comment provided by them would be stored here
    message_id character varying(18),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);

-- user_tip_preferences contains patient's choice of how many tips they want to receive every week
CREATE TABLE public.user_tip_preferences (
    id integer NOT NULL,
    contact_id character varying(18) NOT NULL,
    frequency integer NOT NULL,
    set_by character varying,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);

-- automated_interaction__c contains all the interactions between patients and INA. It also contains patients queries also called as interaction.
-- If patient send message to the INA then input__c would have that and generated_output__c would be null
-- If INA send message to the patient then input__c would null and generated_output__c would have the message
-- NOTE: both input__c and generated_output__c can not be having message in the same row
CREATE TABLE salesforce.automated_interaction__c (
    id character varying(18) NOT NULL,
    name character varying(80) NOT NULL,
    createddate timestamp without time zone NOT NULL,
    createdbyid character varying(18) NOT NULL,
    lastmodifieddate timestamp without time zone NOT NULL,
    lastmodifiedbyid character varying(18) NOT NULL,
    systemmodstamp timestamp without time zone NOT NULL,
    contact__c character varying(18) NOT NULL,
    input__c character varying(32768),
    generated_output__c character varying(32768),
    dialog_entry_type__c character varying(18),
    parent__c character varying(18), -- This field is present for the messages sent by INA to the patient's query. it contains the id of the patient's query. 
    read__c boolean NOT NULL,
    category__c character varying(64),
    subcategory__c character varying(64),
    message_delivery_status character varying(64),
    message_sid character varying(64),
    sent_to_nlp boolean DEFAULT false NOT NULL
);

-- condition__c this stores all conditions reported by patient
CREATE TABLE salesforce.condition__c (
    id character varying(18) NOT NULL,
    ownerid character varying(18) NOT NULL,
    name character varying(80),
    createddate timestamp without time zone NOT NULL,
    createdbyid character varying(18) NOT NULL,
    lastmodifieddate timestamp without time zone NOT NULL,
    lastmodifiedbyid character varying(18) NOT NULL,
    systemmodstamp timestamp without time zone NOT NULL,
    condition_type__c character varying(255),
    contact__c character varying(18),
    stage__c character varying(255)
);

CREATE TABLE salesforce.condition_type__c (
    id character varying(18) NOT NULL,
    ownerid character varying(18) NOT NULL,
    name character varying(80),
    createddate timestamp without time zone NOT NULL,
    createdbyid character varying(18) NOT NULL,
    lastmodifieddate timestamp without time zone NOT NULL,
    lastmodifiedbyid character varying(18) NOT NULL,
    systemmodstamp timestamp without time zone NOT NULL,
    lastvieweddate timestamp without time zone,
    lastreferenceddate timestamp without time zone,
    reference__c character varying(255),
    master_condition__c character varying(18)
);

-- contact stores all the patients. Also called as users or contacts
CREATE TABLE salesforce.contact (
    id character varying(18) NOT NULL,
    lastname character varying(80) NOT NULL,
    firstname character varying(40),
    phone character varying(40),
    birthdate date,
    createddate timestamp without time zone NOT NULL,
    createdbyid character varying(18) NOT NULL,
    endpoint__c character varying(18), -- every user belongs to the group called endpoint. 
    gender__c text,
    height_in_feet__c double precision,
    current_weight__c double precision,
    current_weight_date__c date,
    x1_month_weight__c double precision,
    x1_month_weight_date__c date,
    x6_month_weight__c double precision,
    x6_month_weight_date__c date,
    primary_condition__c character varying(18),
    password__c character varying(64),
    has_authenticated__c boolean NOT NULL,
    initial_intake_completed_by__c text,
    current_bmi__c character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    details jsonb,
    medical_conditions character varying GENERATED ALWAYS AS ((details ->> 'medical_conditions'::text)) STORED,
    allergies character varying GENERATED ALWAYS AS ((details ->> 'allergies'::text)) STORED,
    dietary_preferences character varying GENERATED ALWAYS AS ((details ->> 'dietary_preferences'::text)) STORED
);

CREATE TABLE salesforce.dialog_entry_type__c (
    id character varying(18) NOT NULL,
    ownerid character varying(18) NOT NULL,
    name character varying(80),
    createddate timestamp without time zone NOT NULL,
    createdbyid character varying(18) NOT NULL,
    lastmodifieddate timestamp without time zone NOT NULL,
    lastmodifiedbyid character varying(18) NOT NULL,
    systemmodstamp timestamp without time zone NOT NULL,
    lastvieweddate timestamp without time zone,
    lastreferenceddate timestamp without time zone,
    stage__c character varying(255),
    hash_tag__c character varying(255),
    chain_target__c boolean NOT NULL,
    end_of_topic_in_conversation__c boolean NOT NULL,
    ownership__c character varying(18),
    ownership_type__c text
);

-- dietary_information__c stores all the dietary information submitted by the patient
CREATE TABLE salesforce.dietary_information__c (
    id character varying(18) NOT NULL,
    ownerid character varying(18) NOT NULL,
    name character varying(80),
    createddate timestamp without time zone NOT NULL,
    createdbyid character varying(18) NOT NULL,
    lastmodifieddate timestamp without time zone NOT NULL,
    lastmodifiedbyid character varying(18) NOT NULL,
    systemmodstamp timestamp without time zone NOT NULL,
    allergies_intolerances__c character varying(32768),
    challenges_to_eating_healthy__c character varying(32768),
    contact__c character varying(18),
    dietary_preferences__c character varying(32768)
);

-- endpoint__c this is a group that hold all the patients under it. One endpoint contains multiple patients. 
CREATE TABLE salesforce.endpoint__c (
    id character varying(18) NOT NULL,
    name character varying(80) NOT NULL,
    createddate timestamp without time zone NOT NULL,
    url__c character varying(255),
    sms_inbound_number__c character varying(40), -- Phone number from which this endpoint's users will receive message
    new_session_notification__c character varying(32768),
    default_target_supervised_email__c character varying(80),
    inactive__c boolean NOT NULL, 
    password_required__c boolean NOT NULL,
    soap_note_generation_enabled__c boolean NOT NULL
);

CREATE TABLE salesforce.output_phrase__c (
    id character varying(18) NOT NULL,
    name character varying(80) NOT NULL,
    createddate timestamp without time zone NOT NULL,
    createdbyid character varying(18) NOT NULL,
    lastmodifieddate timestamp without time zone NOT NULL,
    lastmodifiedbyid character varying(18) NOT NULL,
    systemmodstamp timestamp without time zone NOT NULL,
    dialog_phrase__c character varying(18) NOT NULL,
    phrase__c character varying(131072),
    review_date__c date,
    reviewed_by__c character varying(255),
    review_notes__c character varying(32768),
    recommendation__c character varying(18),
    requires_review__c boolean NOT NULL,
    next_dialog_occurrence__c text,
    priority__c text,
    lcsw_review_date__c date,
    md_review_date__c date,
    readability_review_date__c date,
    response_filter__c character varying(255),
    lcsw_initials__c character varying(10),
    md_initials__c character varying(10),
    rn_review_date__c date,
    rn_initials__c character varying(10),
    readability_initials__c character varying(10),
    requires_md_review__c boolean NOT NULL,
    language__c text,
    english_output_phrase__c character varying(18),
    reference__c character varying(18),
    annotation_1__c character varying(255),
    annotation_2__c character varying(255),
    annotation_3__c character varying(255),
    co_morbid_condition__c text,
    reference_2__c character varying(18),
    readability_score__c double precision,
    review_np_initials__c character varying(10),
    np_review_date__c date
);

CREATE TABLE salesforce.phrase__c (
    id character varying(18) NOT NULL,
    name character varying(80) NOT NULL,
    createddate timestamp without time zone NOT NULL,
    createdbyid character varying(18) NOT NULL,
    lastmodifieddate timestamp without time zone NOT NULL,
    lastmodifiedbyid character varying(18) NOT NULL,
    systemmodstamp timestamp without time zone NOT NULL,
    lastvieweddate timestamp without time zone,
    lastreferenceddate timestamp without time zone,
    dialog_phrase__c character varying(18) NOT NULL,
    phrase__c character varying(131072),
    regex__c character varying(32768),
    language__c text,
    english_input_phrase__c character varying(18)
);

-- survey__c contains all the information submitted by the user. 
CREATE TABLE salesforce.survey__c (
    id character varying(18) NOT NULL,
    ownerid character varying(18) NOT NULL,
    name character varying(80),
    createddate timestamp without time zone NOT NULL,
    createdbyid character varying(18) NOT NULL,
    lastmodifieddate timestamp without time zone NOT NULL,
    lastmodifiedbyid character varying(18) NOT NULL,
    systemmodstamp timestamp without time zone NOT NULL,
    lastvieweddate timestamp without time zone,
    lastreferenceddate timestamp without time zone,
    contact__c character varying(18),
    filled_at__c timestamp without time zone,
    survey_code__c character varying(255), -- survey type or code. Data is stored in the text field so should be explicitly cast to jsonb for JSON functions
    survey_content__c character varying(32768) -- survey content is stored in the JSON string format
);

Different types of surveys that patient can submit.

1. "CDC_HEALTHY_MEASURE"
2. "SYMPTOMS_SURVEY"
3. "ADFORCE_SURVEY" -- also known as general intake survey. Submitted by user after sigining up on the platform
4. "TREATEMENT_CHECKIN"
5. "DIETARY_PREFERENCE"
6. "INA_WELL_BEING_CHECKIN"
7. "INITIAL_INTAKE_CANCER" -- Submitted by user after sigining up on the platform
8. "SATISFACTION_SURVEY"

SYMPTOMS_SURVEY content would be stored in following json schema
{
    "Are you having any ongoing symptoms this week (if you are not sure and need to see a list of possible symptoms please select yes)": true, 
    "Please select any current symptoms that you are experiencing.  After you select your symptoms, you will be guided to a question asking you to rank how severe each symptom is.": ["Bloating"], 
    "Bloating": 3, 
    "Name": "Ajinkya", 
    "Phone": "+12014315437"
}

DIETARY_PREFERENCE content would be stored in following json schema
{
    "Do you follow, or have you been asked to follow a specific diet?  Please choose all that apply. ": ["Halal", "Low Fat Diet"], 
    "Do you have any allergies or intolerances to food? Please choose all that apply.": ["Shellfish", "Fish", "Gluten/wheat", "Dairy"], 
    "What are your biggest challenges to eating healthy? Please choose all that apply.": ["TIME: Not enough time to shop and cook"], 
    "Name": "Ajinkya", 
    "Phone": "+12014315437"
}
"""

# Show title and description.
st.title("📄 Data Query")
st.write(
    "Upload a document below and ask a question about it – GPT will answer! "
    "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
)

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:

    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Ask the user for a question via `st.text_area`.
    question = st.text_area(
        "Now ask a question about the data!",
        placeholder="Can you give me a top conditions reported by patients?"
    )

    if question:

        messages = [
            {
                "role": "user",
                "content": f"{PROMPT} \n \n Now you can answer my question: {question}",
            }
        ]

        # Generate an answer using the OpenAI API.
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
        )

        # Stream the response to the app using `st.write_stream`.
        st.write_stream(stream)