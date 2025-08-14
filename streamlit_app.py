#imports
import pandas as pd
import streamlit as st
# import glob
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
pd.options.mode.chained_assignment = None  # default='warn'

# Streamlit page config
st.set_page_config(page_title="CSV File reader",layout="wide")
st.header("Side Quest Hunt")
file_name = st.file_uploader("Upload the Housekeeping Report here", type="csv")

# def load_images():
#     image_files = glob.glob("images/*") # Grabs everything from images


if file_name is not None:
    
    # read in the hsk report
    df = pd.read_csv(file_name,header=0, sep=";", index_col=False ,on_bad_lines='skip')
    
    # conditions for the selected rooms to have a maintenance slot, be free, and not be ooo
    maint_slot = df["Maintenance description"].notna()
    room_free = df["Status"] != "Stay-through"
    not_ooo = df['Maintenance'] != "Out of order"
    rel_df = df[(maint_slot) & (room_free) & (not_ooo)] # df
    
    # exclude PLN slots and put them into a filtered dataframe
    planned_series = rel_df["Maintenance description"].str.contains("PLN", regex= False)
    rel_df["Unplanned"] = planned_series
    filtered_df = rel_df.query('~Unplanned')
    
    # remove undesirable characters from the maintenance description for easier parsing
    filtered_df['Maintenance description'] = filtered_df['Maintenance description'].str.replace('-', ' ') # removes "-" from Maintenance Description for better parsing
    filtered_df['Maintenance description'] = filtered_df['Maintenance description'].str.replace('|', ' ') # removes "|" from Maintenance Description for better parsing
    
    # create a side quest column to emphasize what might be an easy fix
    easy_fix_word_search = ["safe", "tv", "HDMI", "Chromecast", "arc", "charger", "ipad", "cable", "Airplay", "battery", "hairdrier"]
    side_quests = filtered_df["Maintenance description"].str.contains('|'.join(easy_fix_word_search),case=False, regex=True)
    filtered_df["Side Quest Material"] = side_quests
    
    # Only getting relevant columns, and sorting them so that the most likely side quests are at the top
    rel_cols = ["Name", "Condition", "Status", "Occupied", "Maintenance", "Maintenance To", "Maintenance description", "Side Quest Material"]
    final_df = filtered_df[rel_cols].sort_values("Side Quest Material", ascending=False)
    
    # Filter for maintenance to being in the past
    final_df["Maintenance To"] = pd.to_datetime(final_df["Maintenance To"])
    final_df = final_df[final_df["Maintenance To"] > pd.Timestamp.now()]
    
    # Rewrite Occupied column
    bool_dict = {True: "Occupied", False: "Free"}
    final_df["Occupied"] = final_df["Occupied"].map(bool_dict)



    # Export to PDF
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleTitle = styles["Title"]
    
    # Set pagesize to landscape A4
    pdf = SimpleDocTemplate(
        "side_quest_hunt.pdf",
        pagesize=landscape(A4),
        topMargin=10,
        bottomMargin=10,
    )
    
    # Header text
    current_time = pd.Timestamp.now(tz="Europe/London").strftime('%Y-%m-%d %X')
    header = Paragraph(f"Side Quest Hunt Report (Non PL OOS and potentially free rooms) <br/>{current_time}", styleTitle)
    spacer = Spacer(1, 12)  # Space between header and table
    
    # Find the index of the "Maintenance description", and "Side Quest Material" column
    col_names = ["Room number", "Condition", "Status", "Occupied", "Maintenance", "Maintenance Slot Until", "Maintenance description", "Side Quest Material"]
    maintenance_idx = col_names.index("Maintenance description")
    side_quest_material = col_names.index("Side Quest Material")
    name_idx = col_names.index("Room number")
    condition_idx = col_names.index("Condition")
    status_idx = col_names.index("Status")
    occupied_idx = col_names.index("Occupied")
    maintenance_col_idx = col_names.index("Maintenance")


    # Convert the DataFrame to table data with wrapped text in that column
    table_data = [col_names]
    for row in final_df.values.tolist():
        row_copy = row[:]
        row_copy[maintenance_idx] = Paragraph(str(row_copy[maintenance_idx]), styleN)
        table_data.append(row_copy)

    # Set column widths
    # Initialize col_widths with a default width for each column
    col_widths = [115] * len(col_names)

    # Set specific widths for desired columns
    col_widths[name_idx] = 80
    col_widths[condition_idx] = 60
    col_widths[status_idx] = 70
    col_widths[occupied_idx] = 60
    col_widths[maintenance_col_idx] = 70
    col_widths[maintenance_idx] = 180   # wider width for maintenance description
    col_widths[side_quest_material] = 105 # wider width for side quest material
    
    table = Table(table_data, colWidths=col_widths)
    
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ])
    
    table.setStyle(table_style)
    
    # Build PDF with header and table
    pdf.build([header, spacer, table])
    
    # Add download button for PDF
    # Save the PDF to memory
    pdf_buffer = BytesIO()
    pdf = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(A4),
        topMargin=10,
        bottomMargin=10,
    )
    pdf.build([header, spacer, table])
    
    # Move the buffer's position to the start
    pdf_buffer.seek(0)
    
    # Add download button in Streamlit
    st.download_button(
        label="Download PDF",
        data=pdf_buffer,
        file_name="side_quest_hunt.pdf",
        mime="application/pdf"
    )
    st.header("You slay!")


if __name__ == "__main__":
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx() is None:
        from streamlit.web.cli import main
        import sys
        sys.argv = ['streamlit', 'run', __file__]
        main()