# Entry point for Streamlit Community Cloud: runs the app in app/
import os,sys,runpy
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(HERE,'app'))
runpy.run_path(os.path.join(HERE,'app','streamlit_app.py'),run_name='__main__')
