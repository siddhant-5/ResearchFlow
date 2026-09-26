import tempfile
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from Utility import ModelManager, PaperEvaluation
from System import SystemSTORM, SystemClassification
from ThemesAndContext import ThemesAndContext

def generate_pdf(evaluation):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1
    )
    
    elements.append(Paragraph("Paper Evaluation Report", title_style))
    elements.append(Spacer(1, 20))
    
    sections = [
        ("Research Significance", evaluation.significance),
        ("Methodology Assessment", evaluation.methodology),
        ("Presentation Quality", evaluation.presentation),
        ("Major Strengths", evaluation.major_strengths),
        ("Major Weaknesses", evaluation.major_weaknesses),
        ("Score Justification", evaluation.justification),
        ("Detailed Feedback", evaluation.detailed_feedback)
    ]
    
    for title, content in sections:
        elements.append(Paragraph(title, styles['Heading2']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(content, styles['Normal']))
        elements.append(Spacer(1, 20))
    
    scores_data = [
        ['Metric', 'Score'],
        ['Confidence Score', str(evaluation.confidence_score)],
        ['Paper Score', str(evaluation.score)],
        ['Publishable', 'Yes' if evaluation.publishable else 'No']
    ]
    
    scores_table = Table(scores_data, colWidths=[200, 100])
    scores_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(Paragraph("Scores Summary", styles['Heading2']))
    elements.append(Spacer(1, 12))
    elements.append(scores_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def create_report_of_paper(output_model: PaperEvaluation) -> str:
    return " ".join([output_model.significance, output_model.methodology, 
                    output_model.presentation, output_model.justification,
                    output_model.major_strengths, output_model.major_weaknesses,
                    output_model.detailed_feedback])
# Page configuration
st.set_page_config(page_title="Paper Evaluation", page_icon="📜", layout="wide")

# Custom CSS
st.markdown(
    """
    <style>
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .fade-in {
        animation: fadeIn 2s ease-in-out;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #4CAF50;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Main title
st.markdown('<div class="fade-in">Paper Evaluation System 📜</div>', unsafe_allow_html=True)
st.markdown("---")

# API Key handling in sidebar
st.sidebar.title("API Configuration")
groq_api_key = st.sidebar.text_input("Enter Groq API key:", type="password")
model_name= st.sidebar.selectbox("Select Model:",["openai/gpt-oss-120b","qwen/qwen3.8-27b"])
groq_api_key = groq_api_key.strip()
if not model_name:
        model_name= "llama-3.1-8b-instant"
# Initialize LLM and systems
llm = None
classification_system = None
conference_system = None

if groq_api_key:
    llm = ModelManager.get_groq_llm(model_name=model_name, api_key=groq_api_key)

    classification_system = SystemClassification(
        llm=llm,
        debug=True
    )

    conference_system = SystemSTORM(
        llm=llm,
        cvpr_theme=ThemesAndContext.cvpr_theme(),
        cvpr_context=ThemesAndContext.cvpr_context(),
        neur_ips_theme=ThemesAndContext.neur_ips_theme(),
        neur_ips_context=ThemesAndContext.neur_ips_context(),
        emnlp_theme=ThemesAndContext.emnlp_theme(),
        emnlp_context=ThemesAndContext.emnlp_context(),
        kdd_theme=ThemesAndContext.kdd_theme(),
        kdd_context=ThemesAndContext.kdd_context(),
        tmlr_theme=ThemesAndContext.tmlr_theme(),
        tmlr_context=ThemesAndContext.tmlr_context(),
        daa_theme=ThemesAndContext.daa_theme(),
        daa_context=ThemesAndContext.daa_context(),
        wait_time=10,
        debug=True
    )
else:
    st.sidebar.warning("Enter a Groq API key before processing a paper.")

# Main upload section
if not groq_api_key:
    st.warning("Please enter your Groq API key in the sidebar to enable paper processing.")
else:
            
    st.write("Please upload a file size of less than 150 KB")
    uploaded_file = st.file_uploader("Upload your research paper (PDF):", type="pdf")
    process_without_stop_words=False
    with st.expander("Additional Options"):
        process_without_stop_words = st.checkbox("Process Without Stop Words")

    if process_without_stop_words and classification_system is not None:
        st.warning("Processing without stop words might degrade the performance.")

    if classification_system is not None:
        classification_system.split_pdf_without_stop_words = process_without_stop_words

    if uploaded_file:
        if uploaded_file.size > 150 * 1024:  
            st.warning("File size exceeds the limit of 150 KB. This may take up to 50 minutes to process")
        
        if st.button("Process Paper", disabled=not groq_api_key):
            with st.spinner("Processing your paper. This may take 20-55 minutes. Please don't close the browser window."):
                # Save uploaded file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(uploaded_file.read())
                    temp_file_path = temp_file.name
                    
                    # Extract paper ID
                    paper_id = uploaded_file.name[:4]
                    
                    # Process paper
                    output_model = classification_system.classify_paper(path_to_pdf=temp_file_path)
                    
                    if output_model:
                        # Create report summary
                        report_summary = create_report_of_paper(output_model)
                        
                        st.header("Evaluation Results")
                        
                        # Download buttons
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            pdf_buffer = generate_pdf(output_model)
                            st.download_button("Download PDF", pdf_buffer, "evaluation_report.pdf", "application/pdf")
                        with col2:
                            st.download_button("Download JSON", output_model.model_dump_json(indent=2), "evaluation_report.json")
                        with col3:
                            df = pd.DataFrame([output_model.model_dump()]).transpose()
                            df.columns = ['Value']
                            st.download_button("Download CSV", df.to_csv(), "evaluation_report.csv")
                        
                        # Display evaluation details
                        st.subheader("Research Significance")
                        st.write(output_model.significance)
                        
                        st.subheader("Methodology Assessment")
                        st.write(output_model.methodology)
                        
                        st.subheader("Presentation Quality")
                        st.write(output_model.presentation)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Confidence Score", output_model.confidence_score)
                        with col2:
                            st.metric("Paper Score", output_model.score)
                        
                        st.subheader("Major Strengths")
                        st.write(output_model.major_strengths)
                        
                        st.subheader("Major Weaknesses")
                        st.write(output_model.major_weaknesses)
                        
                        st.subheader("Score Justification")
                        st.write(output_model.justification)
                        
                        st.subheader("Detailed Feedback")
                        st.write(output_model.detailed_feedback)
                        
                        st.subheader("Publication Recommendation")
                        st.write("✅ Publishable" if output_model.publishable else "❌ Not Publishable")
                        
                        # Process conference recommendation if publishable
                        if output_model.publishable:
                            st.markdown("---")
                            st.title("Conference Recommendation")
                            
                            with st.spinner("Evaluating the best conference. Please wait..."):
                                conference_decision = conference_system.discuss_and_decide(report_of_paper=report_summary)
                                
                                if conference_decision:
                                    st.header("Recommended Conference")
                                    st.subheader("Conference")
                                    st.write(conference_decision["conference"])
                                    st.subheader("Confidence Score")
                                    st.write(conference_decision["score"])
                                    st.subheader("Justification")
                                    st.write(conference_decision["justification"])
 # Footer
st.markdown("---")