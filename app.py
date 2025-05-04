import streamlit as st
import pdf_handler
import graph
from client import model


def ask_question_on_notes(question, notes_text):
    response = model.generate_content(
        model="gemini-2.0-flash",
        contents=f"Given the following notes: {notes_text}\nAnswer the question: {question}",
    )
    return response.text

def main_app():
    # Session state initialization
    session_defaults = {
        'username': "Guest",
        'uploaded_pdfs': {},
        'selected_pdf': None,
        'quiz_data': {
            'questions': [],
            'index': 0,
            'score': 0,
            'active': False,
            'show_answers': False,
            'answered': {}
        },
        'mindmap': {
            'graph': None,
            'root': None,
            'visible_nodes': set(),
            'current_focus': None
        }
    }

    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # App header
    st.title(f"📚 Study Assistant - {st.session_state.username}")
    
    # Sidebar
    with st.sidebar:
        st.header("Account")
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.header("PDF Tools")
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded_file and uploaded_file.name not in st.session_state.uploaded_pdfs:
            st.session_state.uploaded_pdfs[uploaded_file.name] = uploaded_file
            st.success(f"Added: {uploaded_file.name}")

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📚 Materials", "🗺️ Mind Map", "📝 Quiz"])

    with tab1:  # PDF Materials
        if st.session_state.uploaded_pdfs:
            selected_pdf = st.selectbox(
                "Select PDF", 
                list(st.session_state.uploaded_pdfs.keys()),
                key="pdf_selector"
            )
            st.session_state.selected_pdf = selected_pdf
            
            if selected_pdf:
                pdf_file = st.session_state.uploaded_pdfs[selected_pdf]
                
                with st.expander("📄 PDF Preview", expanded=False):
                    try:
                        pdf_handler.display_pdf_preview(pdf_file)
                    except Exception as e:
                        st.error(f"Failed to display PDF: {str(e)}")
                
                with st.expander("💬 Ask Questions", expanded=False):
                    question = st.text_input("Your question:")
                    if question:
                        with st.spinner("Analyzing content..."):
                            try:
                                pdf_text = pdf_handler.extract_text_from_pdf(pdf_file)
                                response = model.generate_content(
                                    f"Document excerpt: {pdf_text[:5000]}\nQuestion: {question}"
                                )
                                st.info(f"**Answer:** {response.text}")
                            except Exception as e:
                                st.error(f"Failed to generate answer: {str(e)}")

    with tab2:  # Mind Map
        st.header("🧠 Interactive Mind Map")
        
        # Mind map generation form
        with st.form("mindmap_form"):
            generate_btn = st.form_submit_button("Generate Mind Map")
            
            if generate_btn:
                with st.spinner("Building knowledge graph..."):
                    try:
                        graph.initialize_mindmap()
                    except Exception as e:
                        st.error(f"Failed to generate mind map: {str(e)}")

        # Display mind map if exists
        if 'mindmap' in st.session_state and st.session_state.mindmap['graph']:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Show Full View"):
                    st.session_state.mindmap['current_root'] = st.session_state.mindmap['initial_root']
                    st.rerun()
            
            # Draw the interactive mind map
            graph.draw_interactive_mindmap()
            
            # Node information
            if st.session_state.mindmap.get('selected_node'):
                node = st.session_state.mindmap['selected_node']
                desc = st.session_state.mindmap['graph'].nodes[node].get('desc', 'No description available')
                st.markdown(f"**{node}**")
                st.write(desc)
        else:
            st.info("You can now generate a mind map based on the selected PDF")

    with tab3:  # Quiz
        st.header("📝 Knowledge Check")
        
        if st.session_state.selected_pdf:
            pdf_file = st.session_state.uploaded_pdfs[st.session_state.selected_pdf]
            
            with st.expander("⚙️ Quiz Settings", expanded=True):
                cols = st.columns(2)
                with cols[0]:
                    num_questions = st.slider("Questions", 3, 15, 5)
                with cols[1]:
                    difficulty = st.selectbox("Level", ["Easy", "Medium", "Hard"])
                
                if st.button("✨ Generate New Quiz"):
                    with st.spinner("Creating quiz..."):
                        try:
                            pdf_text = pdf_handler.extract_text_from_pdf(pdf_file)
                            if not pdf_text:
                                st.error("No text extracted from PDF")
                                st.stop()
                                
                            quiz_raw = pdf_handler.generate_quiz_questions(
                                pdf_text,
                                num_questions=num_questions,
                                difficulty=difficulty
                            )
                            
                            if not quiz_raw:
                                st.error("Failed to generate quiz content")
                                st.stop()
                                
                            questions = pdf_handler.parse_quiz_questions(quiz_raw)
                            
                            if not questions:
                                st.error("No valid questions parsed")
                                st.stop()
                                
                            st.session_state.quiz_data = {
                                'questions': questions,
                                'index': 0,
                                'score': 0,
                                'active': True,
                                'answered': {}
                            }
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Quiz creation failed: {str(e)}")

            # Quiz display logic
            if st.session_state.get('quiz_data', {}).get('active'):
                quiz = st.session_state.quiz_data
                if not quiz['questions']:
                    st.warning("Quiz generated but no questions available")
                    st.stop()
                    
                current = quiz['questions'][quiz['index']]
                
                st.progress((quiz['index']+1)/len(quiz['questions']))
                st.subheader(f"Question {quiz['index']+1}")
                st.write(current['question'])
                
                selected = st.radio("Options:", current['options'], key=f"q_{quiz['index']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Submit Answer"):
                        if selected == current['answer']:
                            st.success("Correct!")
                            if quiz['index'] not in quiz['answered']:
                                quiz['score'] += 1
                        else:
                            st.error(f"Correct answer: {current['answer']}")
                        quiz['answered'][quiz['index']] = True
                with col2:
                    if quiz['index'] < len(quiz['questions'])-1:
                        if st.button("Next Question"):
                            quiz['index'] += 1
                            st.rerun()
                    else:
                        if st.button("Finish Quiz"):
                            st.balloons()
                            st.success(f"Final score: {quiz['score']}/{len(quiz['questions'])}")
                            quiz['active'] = False
        else:
            st.info("Please select a PDF first")