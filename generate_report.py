import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF  # This script is written for the fpdf2 library
import os
import io  # Import the in-memory buffer library
import re # Import regex for sanitizing filename

# --- 1. CONFIGURATION ---
# The script will auto-extract the prof name from this filename
EXCEL_FILE = 'feedback_FF_Prof. B_Course- Section B_Term- IV_MBA  2024-26.xlsx'

# --- 2. PDF TEMPLATE HELPER ---
class PDF(FPDF):
    """
    This helper class creates a custom PDF template with a
    built-in header and footer (page number).
    """
    def __init__(self, prof_name, *args, **kwargs):
        """
        Store the professor's name when the class is created.
        """
        super().__init__(*args, **kwargs)
        self.prof_name = prof_name

    def header(self):
        self.set_font('Arial', 'B', 15)
        # Use the dynamically passed professor name
        self.cell(0, 10, f'Faculty Feedback Report - {self.prof_name}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

# --- 3. DATA LOADING & PARSING ---
def get_total_submissions(excel_file):
    """
    Reads cell A2 from the first sheet to get the total number of submissions.
    """
    try:
        # sheet_name=0 reads the first sheet
        df_header = pd.read_excel(excel_file, 
                                  sheet_name=0, 
                                  nrows=2, 
                                  header=None)
        cell_a2_value = str(df_header.iloc[1, 0])
        
        if "Submitted answers:" in cell_a2_value:
            total_str = cell_a2_value.split(':')[-1].strip()
            return int(total_str)
        else:
            print("--- ERROR ---")
            print("Could not find 'Submitted answers:' in cell A2.")
            return None
    except Exception as e:
        print(f"--- ERROR reading total submissions: {e} ---")
        return None

def load_and_process_data(excel_file, total_submissions):
    """
    Loads the main data block from the first sheet and processes Q1-Q8
    based on the total_submissions count.
    """
    try:
        # sheet_name=0 reads the first sheet
        df = pd.read_excel(excel_file, 
                           sheet_name=0, 
                           skiprows=4, 
                           header=0)
    except Exception as e:
        print(f"--- ERROR reading main data block: {e} ---")
        return None, None, None, None

    # --- Part 1: Process Quantitative Questions (Q1-Q7) ---
    questions_data = []
    all_averages = [] # To store averages for the grand average
    for i in range(0, 19, 3): # Loops 0, 3, 6, ... 18
        try:
            question_text = df.iloc[i, 1]
            # Get the Likert scale (1, 2, 3...) from the question row
            scores_scale = df.iloc[i, 2:9].astype(float).values
            # Get the counts (1, 6, 6...) from the row *below*
            counts = df.iloc[i + 1, 2:9].astype(float).values
            
            # Calculate weighted sum (C6*C7 + D6*D7 + ...)
            weighted_sum = (scores_scale * counts).sum()
            # Divide by TOTAL submissions, as requested
            average = weighted_sum / total_submissions
            all_averages.append(average) # Add average to list
            
            # --- Calculate percentages (for the chart) ---
            total_count_for_q = counts.sum() # Get sum for *this* question
            if total_count_for_q == 0:
                percentages = [0.0] * 7
            else:
                # Calculate percentage for each of the 7 scores
                percentages = [(count / total_count_for_q) * 100 for count in counts]

            questions_data.append({
                'question': question_text,
                'average': average,
                'percentages': percentages
            })
        except Exception as e:
            print(f"Warning: Could not parse quantitative question at row index {i}. Error: {e}")

    # --- Part 2: Process Qualitative Comments (Q8) ---
    comments_clean = []
    try:
        # Find the start row (where Label == 8.0)
        q8_start_row = df[df['Label'] == 8.0].index[0]
        
        # Define the end row
        end_row = q8_start_row + total_submissions
        
        # Slice the DataFrame to get the N suggestions from Column C
        # (Column index 2 is Column C)
        comments_raw_series = df.iloc[q8_start_row : end_row, 2]

        # Clean the suggestions (Rule: Keep all except blanks)
        for comment in comments_raw_series:
            if pd.isna(comment):
                continue  # It's an empty cell
            
            comment_str = str(comment).strip()
            
            if comment_str: # If the string is not empty ("" or " ")
                comments_clean.append(comment_str)
                    
        print(f"Successfully parsed {len(comments_clean)} specific suggestions.")

    except IndexError:
        print("--- CRITICAL WARNING ---")
        print("Could not find the start of Q8 (Label == 8.0).")
    except Exception as e:
        print(f"Warning: Could not parse text comments for Q8. Error: {e}")

    overall_score = questions_data[6]['average'] 
    # Calculate the new grand average
    grand_average = np.mean(all_averages)
    
    return questions_data, overall_score, comments_clean, grand_average

# --- 4. GRAPH GENERATION ---
def create_distribution_chart(analysis_results):
    """
    Generates the 7-point stacked distribution chart and returns it as
    an in-memory image buffer.
    """
    questions_short = [f"Q{i+1}" for i in range(len(analysis_results))]
    
    # Get percentages for each of the 7 scores
    # (Transposing the data for easier plotting)
    pct_data = np.array([r['percentages'] for r in analysis_results])
    
    # New 7-color palette from Red to Green with more contrast
    colors = ['#a50026', '#d73027', '#f46d43', '#fee090', '#a6d96a', '#1a9850', '#006837']
    legend_labels = ["1", "2", "3", "4", "5", "6", "7"]

    plt.figure(figsize=(10, 5))
    
    bottoms = np.zeros(len(questions_short))
    
    # Loop to create the 7 stacked bars
    for i, (color, label) in enumerate(zip(colors, legend_labels)):
        percentages = pct_data[:, i] # Get all percentages for score 'i'
        plt.bar(questions_short, percentages, bottom=bottoms, label=label, color=color)
        bottoms += percentages # Add to the bottom for the next stack

    plt.ylabel("Percentage of Responses (%)")
    plt.title("Response Distribution per Question")
    
    # Add legend with new title
    legend = plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize='small')
    legend.set_title("Rating")
    
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    
    # Save chart to in-memory buffer instead of file
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300) # Use dpi=300 for clarity
    plt.close()
    img_buffer.seek(0) # Rewind the buffer to the beginning
    
    return img_buffer

# --- 5. PDF CREATION ---
def create_pdf(analysis_results, overall_score, comments_clean, grand_average, chart_image_buffer, prof_name, pdf_output_file):
    """
    Builds the two-page PDF report.
    """
    pdf = PDF(prof_name) # Pass prof_name to the PDF class
    pdf.alias_nb_pages()
    
    # === PAGE 1: Quantitative Report ===
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"Overall Teaching Effectiveness (Q7): {overall_score:.2f} / 7.00", 
             ln=True, align='C')
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Average Scores by Question', ln=True)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(150, 8, 'Question', border=1)
    pdf.cell(40, 8, 'Score ( / 7)', border=1, align='C')
    pdf.ln()
    
    pdf.set_font('Arial', '', 9) 
    for i, item in enumerate(analysis_results):
        q_text = item['question']
        question_text = (q_text[:85] + '...') if len(q_text) > 85 else q_text
        
        pdf.cell(150, 8, f"Q{i+1}. {question_text}", border=1)
        pdf.cell(40, 8, f"{item['average']:.2f}", border=1, align='C')
        pdf.ln()
    
    # Add the new Grand Average row
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(150, 8, 'Overall Average (Q1-Q7)', border=1, align='R')
    pdf.cell(40, 8, f"{grand_average:.2f}", border=1, align='C')
    pdf.ln()
    pdf.ln(5) 

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Response Distribution Visualization', ln=True)
    
    # Embed image from memory buffer
    pdf.image(chart_image_buffer, x=10, w=190, type='PNG')
    pdf.ln(5)

    # === PAGE 2: Qualitative Report (Single Column Layout) ===
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Specific Suggestions to Instructor', ln=True)
    
    pdf.set_font('Arial', '', 10)
    
    if not comments_clean:
        pdf.cell(0, 5, "- No specific suggestions provided.", ln=True)
    else:
        # Reverted to simple, single-column layout
        for comment in comments_clean:
            # multi_cell will handle wrapping long comments
            pdf.multi_cell(0, 5, f"- {comment.strip()}", 0, 'L')
            pdf.ln(1) # 1mm space between comments

    # --- Save the PDF ---
    try:
        pdf.output(pdf_output_file) # Use the dynamic filename
    except PermissionError:
        print(f"--- ERROR ---")
        print(f"Could not save PDF: '{pdf_output_file}'")
        print("Please close the file if it is open in a PDF viewer and try again.")
        return False
    
    return True

# --- 6. MAIN EXECUTION ---
def main():
    print("Report Generation Started...")

    print("1. Extracting professor name...")
    try:
        # Extract name from pattern FF_{name}_Course
        base_filename = os.path.basename(EXCEL_FILE)
        prof_name = base_filename.split('FF_')[1].split('_Course')[0]
    except Exception as e:
        print(f"Warning: Could not auto-detect professor name from file '{EXCEL_FILE}'. Using default 'Faculty'.")
        print(f"Error details: {e}")
        prof_name = "Faculty"
    print(f"Professor name found: {prof_name}")
    
    # Sanitize name for filename (remove characters Windows doesn't like)
    sanitized_name = re.sub(r'[.\\/*?"<>|:]', '', prof_name)
    PDF_OUTPUT_FILE = f'Feedback_Report_{sanitized_name}.pdf'


    print("2. Reading total submissions...")
    total_submissions = get_total_submissions(EXCEL_FILE)
    
    if total_submissions is None:
        print("Exiting due to error.")
        return
    print(f"Found {total_submissions} total submissions.")

    print("3. Loading and processing main data...")
    questions_data, overall_score, comments_clean, grand_average = load_and_process_data(
        EXCEL_FILE, total_submissions
    )
    
    if questions_data is None:
        print("Exiting due to error.")
        return

    print("4. Generating distribution chart...")
    chart_image_buffer = create_distribution_chart(questions_data)

    print(f"5. Building PDF report ('{PDF_OUTPUT_FILE}')...")
    pdf_saved = create_pdf(
        questions_data, 
        overall_score, 
        comments_clean, 
        grand_average, 
        chart_image_buffer,
        prof_name, # Pass the extracted name
        PDF_OUTPUT_FILE # Pass the new dynamic filename
    )
    
    if pdf_saved:
        # No more files to clean up
        print("\n--- Success! ---")
        print(f"Report saved as: {PDF_OUTPUT_FILE}")
        print("----------------")
    
if __name__ == "__main__":
    main()