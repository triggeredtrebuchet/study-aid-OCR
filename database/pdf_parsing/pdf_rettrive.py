import time
from google.genai import types
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
genai.configure(api_key="API_KEY")

class PDFRetriver:
    def __init__(self, pdf_parser = None):
        # self.client = genai.Client(api_key='')
        self.nubmer_of_context_chunks = 3
        self.pdf_parser = pdf_parser
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def embed_question(self, question):
        input_to_model = question
        for _ in range(3):
            try:
                response = self.client.models.embed_content(model="gemini-embedding-exp-03-07", contents=question, config=types.EmbedContentConfig(
                      task_type="RETRIEVAL_QUERY",
                    ))
                success = True
            except Exception as e:
                print(f"Error embedding question: {question}")
                print(f"Error message: {e}")
                time.sleep(60)
                success = False
            if success:
                break
        if not success:
            raise Exception("Failed to embed question after multiple attempts.")

        return response.embeddings[0].values

    def embed_query(self, query: str, model="models/embedding-001"):
        """Embeds a search query optimized for retrieval"""
        return genai.embed_content(
            model=model,
            content=query,
            task_type="RETRIEVAL_QUERY"  # Critical for queries
        )['embedding']

    def gen_response(self, question):
        """Generates a response to a question using the model"""
        print(question)
        try:
            response = self.model.generate_content(question)
            return response.text
        except Exception as e:
            print(f"Error generating response: {e}")
            return None

    def load_vectors(self, user_id):
        # Load the vector entries from the database
        import pickle
        self.pdf_parser.last_ve = pickle.load(open("ve.pkl", "rb"))
        for i in range(len(self.pdf_parser.last_ve)):
            self.pdf_parser.last_ve[i].id = i
        print(self.pdf_parser.last_ve)
        return self.pdf_parser.last_ve

    def compare_vectors(self, question_vector, vectors):
        # Compare the question vector with the loaded vectors
        similarities = []
        for ve in vectors:
            similarity = cosine_similarity([question_vector], [ve.vector])
            similarities.append((similarity, ve.id))

        # Sort by similarity
        similarities.sort(reverse=True, key=lambda x: x[0])
        return similarities[:self.nubmer_of_context_chunks]

    def load_vector_by_id(self, vector_id):
        # Load the vector entry by its ID
        out = []
        for ve in self.pdf_parser.last_ve:
            if ve.id == vector_id:
                out.append(ve)
        return out

    def concatenate_question_and_context(self, question, context):
        # Concatenate the question and the context
        print(context)
        context = " ".join([ve[0].text_chunk for ve in context])
        return f"Based on the following context: {context}\nAnswer the question: {question}"

    def generate_answer(self, question):
        # Generate the answer using the concatenated question and context
        question_vector = self.embed_query(question)
        vectors = self.load_vectors(user_id=None)
        context = self.compare_vectors(question_vector, vectors)
        context = [self.load_vector_by_id(ve[1]) for ve in context]
        return self.gen_response(self.concatenate_question_and_context(question, context))