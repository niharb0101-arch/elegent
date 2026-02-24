import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# ==========================================
# 1. Database Initialization
# ==========================================
def init_db():
    conn = sqlite3.connect('student_performance.db', check_same_thread=False)
    c = conn.cursor()
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS subjects (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY, class_name TEXT, name TEXT, age INTEGER, 
                    parent_names TEXT, parent_occ TEXT, phone TEXT, living_area TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY, student_id INTEGER, subject_name TEXT, 
                    review_date TEXT, edu_review TEXT, disc_review TEXT, parent_notes TEXT)''')
    
    # Insert default subjects if none exist
    c.execute("SELECT count(*) FROM subjects")
    if c.fetchone()[0] == 0:
        for subj in ['Maths', 'EVS', 'Social', 'English']:
            c.execute("INSERT INTO subjects (name) VALUES (?)", (subj,))
            
    conn.commit()
    return conn

conn = init_db()

# ==========================================
# 2. Helper Functions
# ==========================================
def get_classes():
    return [row[0] for row in conn.execute("SELECT name FROM classes").fetchall()]

def get_students(class_name):
    return pd.read_sql_query(f"SELECT * FROM students WHERE class_name='{class_name}'", conn)

def get_subjects():
    return [row[0] for row in conn.execute("SELECT name FROM subjects").fetchall()]

# ==========================================
# 3. Page Configurations & Navigation
# ==========================================
st.set_page_config(page_title="Student Performance Manager", layout="wide")
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home / Review Entry", "Summary Page", "Settings", "Export"])

# ==========================================
# 4. Settings Page (Class & Student Management)
# ==========================================
if page == "Settings":
    st.header("⚙️ Settings & Management")
    
    tab1, tab2, tab3 = st.tabs(["Manage Classes", "Manage Students", "Manage Subjects"])
    
    with tab1:
        st.subheader("Add New Class")
        new_class = st.text_input("Class Name (e.g., Class 1A)")
        if st.button("Add Class"):
            try:
                conn.execute("INSERT INTO classes (name) VALUES (?)", (new_class,))
                conn.commit()
                st.success(f"Class '{new_class}' added successfully!")
            except sqlite3.IntegrityError:
                st.error("Class already exists.")
                
    with tab2:
        st.subheader("Add New Student")
        classes = get_classes()
        if classes:
            sel_class = st.selectbox("Assign to Class", classes)
            s_name = st.text_input("Student Name")
            s_age = st.number_input("Age", min_value=3, max_value=20)
            s_parents = st.text_input("Parent Names")
            s_occ = st.text_input("Parent Occupation")
            s_phone = st.text_input("Phone Number")
            s_area = st.text_input("Living Area")
            
            if st.button("Save Student"):
                conn.execute('''INSERT INTO students (class_name, name, age, parent_names, parent_occ, phone, living_area) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                             (sel_class, s_name, s_age, s_parents, s_occ, s_phone, s_area))
                conn.commit()
                st.success(f"Student '{s_name}' added to {sel_class}!")
        else:
            st.warning("Please add a class first.")

# ==========================================
# 5. Home / Review Entry Page
# ==========================================
elif page == "Home / Review Entry":
    st.header("📝 Review Entry System")
    
    classes = get_classes()
    if not classes:
        st.info("No classes found. Please add classes and students in Settings.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            sel_class = st.selectbox("Select Class", classes)
        
        students_df = get_students(sel_class)
        if students_df.empty:
            st.warning(f"No students found in {sel_class}.")
        else:
            with col2:
                sel_student = st.selectbox("Select Student", students_df['name'].tolist())
            
            # Display Preset Profile Data
            st.markdown("---")
            st.subheader(f"Profile: {sel_student}")
            student_data = students_df[students_df['name'] == sel_student].iloc[0]
            st.write(f"**Age:** {student_data['age']} | **Parents:** {student_data['parent_names']} | **Phone:** {student_data['phone']}")
            st.markdown("---")
            
            # Review Entry Setup
            review_date = st.date_input("Date", date.today())
            subjects = get_subjects()
            
            if subjects:
                # Create dynamic tabs for subjects
                tabs = st.tabs(subjects)
                for i, subj in enumerate(subjects):
                    with tabs[i]:
                        st.subheader(f"{subj} Review")
                        
                        # Add new review form
                        with st.expander(f"➕ Add New Entry for {subj}"):
                            with st.form(key=f"form_{subj}"):
                                edu_rev = st.text_area("Educational Review")
                                disc_rev = st.text_area("Discipline Review")
                                par_notes = st.text_area("Notes to Parents")
                                submit_btn = st.form_submit_button("Save Review")
                                
                                if submit_btn:
                                    conn.execute('''INSERT INTO reviews (student_id, subject_name, review_date, edu_review, disc_review, parent_notes)
                                                    VALUES (?, ?, ?, ?, ?, ?)''', 
                                                 (int(student_data['id']), subj, review_date, edu_rev, disc_rev, par_notes))
                                    conn.commit()
                                    st.success("Review saved!")
                        
                        # Display previous reviews for this subject
                        st.markdown("**Recent Reviews**")
                        reviews_df = pd.read_sql_query(f'''
                            SELECT review_date as Date, edu_review as "Educational Review", 
                                   disc_review as "Discipline Review", parent_notes as "Notes to Parents"
                            FROM reviews 
                            WHERE student_id={student_data['id']} AND subject_name='{subj}' 
                            ORDER BY review_date DESC
                        ''', conn)
                        st.dataframe(reviews_df, use_container_width=True)

# ==========================================
# 6. Summary Page (View Only)
# ==========================================
elif page == "Summary Page":
    st.header("📊 Student Summary Dashboard")
    
    classes = get_classes()
    if classes:
        sel_class = st.selectbox("Select Class", classes, key="sum_class")
        students_df = get_students(sel_class)
        if not students_df.empty:
            sel_student = st.selectbox("Select Student", students_df['name'].tolist(), key="sum_student")
            student_data = students_df[students_df['name'] == sel_student].iloc[0]
            
            st.markdown(f"### Chronological Summary for {sel_student}")
            all_reviews = pd.read_sql_query(f'''
                SELECT review_date as Date, subject_name as Subject, edu_review as "Educational Review", 
                       disc_review as "Discipline", parent_notes as "Parent Notes"
                FROM reviews 
                WHERE student_id={student_data['id']}
                ORDER BY review_date DESC
            ''', conn)
            st.dataframe(all_reviews, use_container_width=True)

# ==========================================
# 7. Export Functionality
# ==========================================
elif page == "Export":
    st.header("📥 Export Data")
    st.write("Select data to export as CSV.")
    
    if st.button("Export All Students Data (CSV)"):
        df = pd.read_sql_query("SELECT * FROM students", conn)
        csv = df.to_csv(index=False)
        st.download_button("Download Students CSV", csv, "students_export.csv", "text/csv")
        
    if st.button("Export All Reviews Data (CSV)"):
        df = pd.read_sql_query("SELECT * FROM reviews", conn)
        csv = df.to_csv(index=False)
        st.download_button("Download Reviews CSV", csv, "reviews_export.csv", "text/csv")

# Close connection at the end of script
conn.close()
