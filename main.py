import streamlit as st


def main_ui():
    pg = st.navigation(
        [
            st.Page("pages/home.py", title="Domů", icon=":material/home:"),
        ])
    pg.run()

if __name__ == "__main__":
    st.set_page_config(layout="wide")


    # HACK https://discuss.streamlit.io/t/hide-deploy-and-streamlit-mainmenu/52433/2
    st.markdown("""
        <style>
            .reportview-container {
                margin-top: -2em;
            }
            #MainMenu {visibility: hidden;}
            .stAppDeployButton {display:none;}
            footer {visibility: hidden;}
            #stDecoration {display:none;}
        </style>
    """, unsafe_allow_html=True)

    main_ui()