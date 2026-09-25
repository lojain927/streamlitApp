from datetime import datetime
import io
import random
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ------------------------------------------------------------------
# 1. إعدادات الصفحة والتصميم الملكي بالألوان النهدية والبيج
# ------------------------------------------------------------------
st.set_page_config(
    page_title="نظام مَلاذ | Malath System",
    page_icon="🎀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* خلفية التطبيق بيج دافئ وناعم */
    .stApp { background-color: #FAF5EF; }
    
    /* العناوين باللون النهدي والبنفسجي الملكي */
    .royal-title { color: #4A148C; text-align: center; font-size: 2.4rem; font-weight: 800; }
    .royal-sub { color: #7B1FA2; text-align: center; font-size: 1.1rem; margin-bottom: 20px; }
    
    /* الأزرار باللون النهدي والزهري الناعم */
    .stButton>button { 
        background: linear-gradient(135deg, #8E24AA 0%, #D81B60 100%); 
        color: white !important; 
        border-radius: 10px; 
        font-weight: bold; 
        border: none;
        padding: 10px;
    }
    
    /* النماذج والبطاقات */
    div[data-testid="stForm"] { 
        background-color: #FFF9F3; 
        border-radius: 16px; 
        padding: 25px; 
        border: 2px solid #E1BEE7; 
        box-shadow: 0px 4px 15px rgba(142, 36, 170, 0.08);
    }
    
    /* بطاقات الاستراحة والأنشطة */
    .fun-card { 
        background-color: #F3E5F5; 
        padding: 15px; 
        border-radius: 12px; 
        border-right: 5px solid #D81B60; 
        color: #4A148C;
        margin-top: 10px;
    }
    
    /* إطار الصورة المدمجة */
    .blended-box {
        text-align: center;
        background-color: #FFF9F3;
        padding: 15px;
        border-radius: 20px;
        border: 2px solid #E1BEE7;
        box-shadow: 0 4px 15px rgba(142, 36, 170, 0.1);
        margin-bottom: 20px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# 2. إعدادات قاعدة البيانات المباشرة والخفيفة (SQLite)
# ------------------------------------------------------------------
DB_FILE = "malath_db.db"


def get_connection():
  return sqlite3.connect(DB_FILE)


def init_db():
  try:
    conn = get_connection()
    cursor = conn.cursor()

    # جدول المستخدمين للتسجيل والدخول
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # جدول سجلات المريضات
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                city TEXT NOT NULL,
                stage TEXT NOT NULL,
                gestational_detail TEXT,
                booking_reason TEXT,
                chronic TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                complaint TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    conn.close()
  except Exception as err:
    st.error(f"❌ Database Error: {err}")


# ------------------------------------------------------------------
# 3. دالة التصنيف التلقائي لدرجة الخطورة (Automated Risk Assessment)
# ------------------------------------------------------------------
def evaluate_risk_automatically(age, chronic, complaint, stage):
  """تحليل مدخلات المريضة وتحديد مستوى الخطورة تلقائياً"""
  high_risk_keywords = [
      "نزيف",
      "ضغط مرتفع",
      "تسمم حمل",
      "صداع شديد",
      "زغللة",
      "آلام شديدة",
      "تجلط",
      "قلة حركة",
  ]
  mod_risk_keywords = [
      "غثيان مستمر",
      "سكر",
      "فقر دم",
      "أنيميا",
      "إرهاق",
      "الم ظهر",
      "التهاب",
  ]

  complaint_lower = complaint.lower() if complaint else ""

  # فحص حالات الخطورة العالية 🔴
  if (
      chronic == "نعم"
      or age >= 38
      or age <= 16
      or any(kw in complaint_lower for kw in high_risk_keywords)
  ):
    return (
        "🔴 High Risk",
        "تنبيه: الحالة تتطلب متابعة طبية حثيثة وفحوصات دورية مكثفة.",
    )

  # فحص حالات الخطورة المتوسطة 🟡
  elif any(kw in complaint_lower for kw in mod_risk_keywords) or (
      stage == "أثناء الحمل" and (age > 33 or age < 18)
  ):
    return (
        "🟡 Moderate Risk",
        "ملاحظة: الحالة تتطلب استشارة ومتابعة منتظمة لضمان الاستقرار.",
    )

  # الحالات المستقرة 🟢
  else:
    return "🟢 Low Risk", "الحالة مستقرة وطبيعية بفضل الله."


def draw_chart(df):
  fig, ax = plt.subplots(figsize=(7, 3.5))
  risk_counts = df["risk_level"].value_counts()
  colors = []
  for idx in risk_counts.index:
    if "High" in idx:
      colors.append("#E53935")
    elif "Moderate" in idx:
      colors.append("#FB8C00")
    else:
      colors.append("#43A047")

  ax.bar(risk_counts.index, risk_counts.values, color=colors)
  ax.set_xlabel("مستوى الخطورة التلقائي")
  ax.set_ylabel("عدد الحالات")
  ax.set_title("توزيع المريضات حسب تقييم الخطورة")
  fig.tight_layout()
  st.pyplot(fig)


init_db()

if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False

# ------------------------------------------------------------------
# 4. الشاشة الأولى: تسجيل الدخول وإنشاء حساب جديد (Register / Login)
# ------------------------------------------------------------------
if not st.session_state["logged_in"]:
  st.markdown(
      '<p class="royal-title">🎀 أهلاً بكِ في المَملكة الطبيّة لـ مَلاذ</p>',
      unsafe_allow_html=True,
  )
  st.markdown(
      '<p class="royal-sub">✨ المنصة الملكية الفاخرة للياقة ورعاية الأمهات'
      " والملكات الحوامل ✨</p>",
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 2, 1])

  with col2:
      # --- كود البحث التلقائي عن الصورة وعرضها ---
      import glob
      import os

      st.markdown('<div class="blended-box">', unsafe_allow_html=True)

      # يبحث عن أي صورة موجودة بالمجلد مهما كان اسمها
      image_files = (
          glob.glob("*.png")
          + glob.glob("*.jpg")
          + glob.glob("*.jpeg")
          + glob.glob("*.JPG")
          + glob.glob("*.PNG")
      )

      if image_files:
       # --- عرض الصورة المقصوصة (mom and dad) بنفس الأبعاد العريضة الأنيقة ---
        import os

        # البحث عن اسم الصورة الجديدة تحديداً لمنع الرجوع للصورة القديمة
        target_image = None
        possible_names = [
            
         "malath_bannar.png",
        
        ]

        for name in possible_names:
          if os.path.exists(name):
            target_image = name
            break

        # إذا لم يجد الاسم الجديد، يستخدم أي صورة متاحة بالمجلد
        if not target_image and image_files:
          target_image = image_files[0]

        if target_image:
          # عرض الصورة بحاوية عريضة وقصيرة الارتفاع
          import base64

          with open(target_image, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode("utf-8")

          st.markdown(
              f"""
                <div style="display: flex; justify-content: center; align-items: center; width: 100%; margin: 10px 0 20px 0;">
                    <div style="
                        width: 100%; 
                        max-width: 600px; 
                        height: 180px; 
                        overflow: hidden; 
                        border-radius: 14px; 
                        box-shadow: 0 4px 15px rgba(0,0,0,0.06);
                        border: 1px solid #f3e5f5;
                        background-color: #ffffff;
                    ">
                        <img src="data:image/png;base64,{encoded_image}" style="
                            width: 100%; 
                            height: 100%; 
                            object-fit: cover; 
                            object-position: center 30%;
                        ">
                    </div>
                </div>
                """,
              unsafe_allow_html=True,
          )
        else:
          st.markdown(
              "<h3 style='text-align: center;'>🎀 نظام مَلاذ الطبي</h3>",
              unsafe_allow_html=True,
          )
          st.write(
              "✨ *مَلاذ.. احتضان الحنان والأمان لكل أم وطفل تحت إشراف القابلة"
              " القانونية لجين* ✨"
          )

        st.markdown("</div>", unsafe_allow_html=True)
      tab_login, tab_register = st.tabs(
        ["🔑 تسجيل الدخول", "📝 حساب جديد (Register)"]
    )

    # تبويب تسجيل الدخول
      with tab_login:
        st.markdown("### 🏛️ تسجيل الدخول")
      with st.form("login_form"):
        file_id_input = st.text_input(
            "📂 رقم الملف الطبي (File ID)", placeholder="مثال: M-101"
        )
        password_input = st.text_input(
            "🔑 كلمة السر (Password)", type="password"
        )
        login_btn = st.form_submit_button("دخول إلى النظام 🚀")

        if login_btn:
          f_clean = file_id_input.strip()
          if f_clean == "M-101" and password_input == "1234":
            st.session_state["logged_in"] = True
            st.session_state["file_id"] = f_clean
            st.session_state["user_name"] = "MW.LOJAIN"
            st.success("تم تسجيل الدخول بنجاح! 🎀")
            st.rerun()
          elif f_clean != "" and password_input != "":
            try:
              conn = get_connection()
              cursor = conn.cursor()
              cursor.execute(
                  "SELECT name, password FROM users WHERE file_id = ?",
                  (f_clean,),
              )
              user = cursor.fetchone()
              conn.close()

              if user and user[1] == password_input:
                st.session_state["logged_in"] = True
                st.session_state["file_id"] = f_clean
                st.session_state["user_name"] = user[0]
                st.success(f"أهلاً بكِ {user[0]}! 🎀")
                st.rerun()
              else:
                st.error("⚠️ رقم الملف أو كلمة السر غير صحيحة.")
            except Exception as e:
              st.error(f"❌ خطأ: {e}")
          else:
            st.warning("⚠️ يرجى تعبئة الحقول الأساسية.")

    # تبويب إنشاء حساب جديد
      with tab_register:
        st.markdown("### 🎀 الانضمام لعائلة مَلاذ")
      with st.form("register_form"):
        new_name = st.text_input("👤 الاسم الكامل", placeholder="مثال: د. لجين")
        new_file_id = st.text_input(
            "📂 رقم الملف الطبي الجديد", placeholder="مثال: M-102"
        )
        new_password = st.text_input(
            "🔑 كلمة السر", type="password", placeholder="كلمة السر"
        )
        confirm_pass = st.text_input(
            "🔒 تأكيد كلمة السر", type="password", placeholder="إعادة كلمة السر"
        )

        reg_btn = st.form_submit_button("تأكيد وإنشاء الحساب ✨")

        if reg_btn:
          if not new_name.strip() or not new_file_id.strip():
            st.warning("⚠️ يرجى تعبئة كافة الحقول.")
          elif new_password != confirm_pass:
            st.error("⚠️ كلمات السر غير متطابقة!")
          else:
            try:
              conn = get_connection()
              cursor = conn.cursor()
              cursor.execute(
                  "INSERT INTO users (file_id, name, password) VALUES (?, ?,"
                  " ?)",
                  (new_file_id.strip(), new_name.strip(), new_password),
              )
              conn.commit()
              conn.close()
              st.success(
                  "🎀 تم إنشاء الحساب بنجاح! يمكنكِ الآن تسجيل الدخول."
              )
              st.balloons()
            except sqlite3.IntegrityError:
              st.error("⚠️ رقم الملف الطبي مستخدم مسبقاً!")
            except Exception as err:
              st.error(f"❌ خطأ: {err}")

# ------------------------------------------------------------------
# 5. الشاشة الثانية: القائمة الجانبية والنظام الرئيسي
# ------------------------------------------------------------------
else:
  with st.sidebar:
    st.title("🎀 نظام مَلاذ")
    st.caption(
        f"المستخدم: **{st.session_state.get('user_name', 'القابلة')}** |"
        f" ({st.session_state['file_id']})"
    )
    st.divider()

    page = st.radio(
        "📍 القائمة الرئيسية:",
        [
            "📝 حجز وتكفل حالة جديدة",
            "📊 سجل البيانات والتحليل التلقائي",
            "ℹ️ من نحن (About Us)",
        ],
    )

    st.divider()

    # فقرة التسلية والموضوعات المتغيرة للأم والحوامل
    st.markdown("### ☕ استراحة ومواضيع للتسلية")
    topics = [
        {
            "title": "👶 إحساس الجنين بحنان الأم",
            "content": (
                "عندما تحتضن الأم طفلها أو تلمس بطنها، تنتقل ذبذبات الأمان"
                " وينتظم نبض قلب الجنين فوراً."
            ),
        },
        {
            "title": "🥑 حقيقة حجم طفلك",
            "content": (
                "في الأسبوع الـ 20 من الحمل، يكون حجم الجنين مساوياً لحبة أفوكادو"
                " لطيفة!"
            ),
        },
        {
            "title": "🎵 صوت الأم والموسيقى",
            "content": (
                "يميز الجنين نبرة صوت أمه ابتداءً من الشهر السادس ويميل للهدوء"
                " عند سماعها."
            ),
        },
    ]

    if "topic_idx" not in st.session_state:
      st.session_state["topic_idx"] = 0

    cur_topic = topics[st.session_state["topic_idx"]]
    st.markdown(
        f"""
        <div class="fun-card">
            <b>{cur_topic['title']}</b><br>
            <p style="font-size: 0.88rem; margin-top: 5px;">{cur_topic['content']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🎲 موضوع آخر للتسلية"):
      st.session_state["topic_idx"] = (
          st.session_state["topic_idx"] + 1
      ) % len(topics)
      st.rerun()

    st.divider()
    if st.button("تسجيل الخروج 🚪"):
      st.session_state["logged_in"] = False
      st.rerun()

  # --------------------------------------------------
  # الصفحة الأولى: حجز حالة جديدة مع التصنيف التلقائي
  # --------------------------------------------------
  if page == "📝 حجز وتكفل حالة جديدة":
    st.subheader("📋 تسجيل حالة جديدة مع تقييم تلقائي للخطورة")

    with st.form("patient_form"):
      col1, col2 = st.columns(2)
      with col1:
        name = st.text_input("👤 اسم المريضة الثلاثي")
        age = st.number_input("🔢 العمر", min_value=12, max_value=60, value=25)
        city = st.text_input("📍 المدينة / المنطقة", value="عمان")
        booking_reason = st.selectbox(
            "🎯 سبب الحجز والزيارة",
            [
                "متابعة دورية للحمل",
                "استشارة طبية طارئة",
                "فحص ألتراساوند (سونار)",
                "متابعة ما بعد الولادة",
                "تخطيط للحمل",
            ],
        )

      with col2:
        stage = st.selectbox(
            "🤰 مرحلة الحمل الحالية",
            ["ما قبل الحمل", "أثناء الحمل", "مرحلة الولادة وما بعدها"],
        )

        gestational_detail = "غير محدد"
        if stage == "أثناء الحمل":
          sc1, sc2 = st.columns(2)
          with sc1:
            month = st.selectbox(
                "📅 الشهر", [f"الشهر {i}" for i in range(1, 10)]
            )
          with sc2:
            week = st.number_input(
                "⏳ الأسبوع", min_value=1, max_value=42, value=12
            )
          gestational_detail = f"{month} - الأسبوع {week}"

        chronic = st.radio(
            "🩺 هل يوجد أمراض مزمنة؟", ["لا", "نعم"], horizontal=True
        )

      complaint = st.text_area(
          "💬 الشكوى الرئيسية / الأعراض والآلام الحالية",
          placeholder=(
              "اكتبي الشكوى هنا (مثال: نزيف، صداع شديد، غثيان، آلام بالظهر...)"
          ),
      )

      save_btn = st.form_submit_button(
          "تأكيد الحجز والتحليل التلقائي للحالة 💾"
      )

      if save_btn:
        if not name.strip() or not city.strip():
          st.warning("⚠️ يرجى تعبئة كافة البيانات الأساسية.")
        else:
          # إجراء التصنيف التلقائي
          auto_risk, risk_note = evaluate_risk_automatically(
              age, chronic, complaint, stage
          )

          try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                            INSERT INTO patients (file_id, name, age, city, stage, gestational_detail, booking_reason, chronic, risk_level, complaint)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                (
                    st.session_state["file_id"],
                    name,
                    age,
                    city,
                    stage,
                    gestational_detail,
                    booking_reason,
                    chronic,
                    auto_risk,
                    complaint,
                ),
            )
            conn.commit()
            conn.close()

            st.success(
                f"✨ تم حفظ الحالة بنجاح! النتيجة التلقائية: **{auto_risk}**"
            )
            st.info(f"💡 {risk_note}")
            st.balloons()
          except Exception as err:
            st.error(f"❌ خطأ أثناء الحفظ: {err}")

  # --------------------------------------------------
  # الصفحة الثانية: سجل البيانات وتصدير Excel
  # --------------------------------------------------
  elif page == "📊 سجل البيانات والتحليل التلقائي":
    st.subheader("📊 لوحة السجلات وتصدير Excel")

    try:
      conn = get_connection()
      df = pd.read_sql("SELECT * FROM patients", conn)
      conn.close()

      if df.empty:
        st.info("ℹ️ لا توجد حالات مسجلة حتى الآن.")
      else:
        total = len(df)
        high_risk = len(
            df[df["risk_level"].str.contains("High Risk", na=False)]
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("إجمالي الحالات 📋", f"{total}")
        m2.metric("حالات عالية الخطورة 🚨", f"{high_risk}")
        m3.metric("نظام التقييم ⚡", "تلقائي (مبني على الخوارزمية)")

        st.divider()

        # تصدير Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
          df.to_excel(writer, index=False, sheet_name="Malath_Patients")

        st.download_button(
            label="📊 تنزيل ملف Excel الكامل (.xlsx)",
            data=buffer.getvalue(),
            file_name="malath_patients_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.divider()
        st.write("### 📋 جدول الحالات والتصنيف التلقائي")
        st.dataframe(df, use_container_width=True)

        st.divider()
        draw_chart(df)

    except Exception as err:
      st.error(f"❌ خطأ: {err}")

  # --------------------------------------------------
  # الصفحة الثالثة: من نحن
  # --------------------------------------------------
  elif page == "ℹ️ من نحن (About Us)":
      st.markdown(
          '<p class="royal-title">🎀 نظام مَلاذ الطبي | Malath System</p>',
          unsafe_allow_html=True,
      )
      st.markdown(
          '<p class="royal-sub">✨ الرعاية الأمثل والاحتضان الدافئ لكل أم'
          " وطفل ✨</p>",
          unsafe_allow_html=True,
      )
      st.divider()

      col_img, col_text = st.columns([1, 1.5])

      
        

      with col_text:
            st.markdown("""
            ### 📜 عن النظام
            تم تصميم وتطوير **نظام مَلاذ الطبي** بحرص وعناية فائقة بواسطة **القابلة القانونية لجين**، ليكون بيئة رقمية آمنة ومتكاملة تخدم صحة المرأة والحامل والرعاية الصحية الأولية.

            ---

            ### 🎯 الرؤية والهدف
            * **التصنيف الذكي:** تقديم تقييم تلقائي فوري لمستوى الخطورة بناءً على الأعراض المدخلة لضمان أولوية الرعاية.
            * **الخصوصية والأمان:** إدارة سجلات المريضات وتتبع الحالات بكل سهولة ودقة.
            * **الدعم والتوعية:** توفير مساحة دافئة ومحتوى توعوي يدعم الأم أثناء رحلتها المباركة.

            ---
            > 🎀 *تطوير وإشراف: القابلة القانونية لجين*
            """)