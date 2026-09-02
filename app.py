ठीक है। नीचे अपडेटेड और बेहतर कोड दे रहा हूँ।
इसमें प्रॉम्प्ट को और मजबूत किया गया है ताकि AI ज्यादा स्मार्ट, फास्ट और प्रोफेशनल स्ट्रेटजी दे।
import os
from groq import Groq

# Render से API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.markdown("### 💬 GYAN AI Pro ट्रेडिंग मेंटर से सीधी बातचीत")
st.markdown("यहाँ आप Universal Trading Institute के इस AI मेंटर से किसी भी कॉइन या अपनी ट्रेडिंग स्ट्रेटजी के बारे में हिंदी में चर्चा कर सकते हैं।")

chat_symbol = st.selectbox("चैट के लिए सिंबल चुनें", symbols_list, key="chat_sym")

if "messages" not in st.session_state:
    st.session_state.messages = []

# पुराने मैसेज दिखाओ
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_query := st.chat_input("जैसे पूछें: 'इस कॉइन में फास्ट ट्रेड दो' या 'स्केलपिंग स्ट्रेटजी बताओ'"):
    st.session_state.messages.append({"role": "user", "content": user_query})

    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("GYAN AI मेंटर जवाब तैयार कर रहा है..."):
            try:
                ticker = get_ticker(chat_symbol)
                price = ticker.get("mark_price", "N/A")

                system_prompt = f"""
आप GYAN AI Pro के बहुत स्मार्ट, फास्ट और प्रोफेशनल ट्रेडिंग मेंटर हैं।
आप हमेशा शुद्ध और आसान हिंदी में जवाब देते हैं।

आपका मुख्य लक्ष्य:
- जल्दी प्रॉफिट वाले Fast Trading / Scalping स्ट्रेटजी बनाना
- हर स्ट्रेटजी को साफ और लॉजिकल रखना
- Entry, Stop Loss और Take Profit सटीक बताना
- रिस्क कम रखना और जल्दी प्रॉफिट बुक करवाना

हर जवाब में ये फॉर्मेट जरूर फॉलो करें:

**1. स्ट्रेटजी का नाम:**  
(छोटा और साफ नाम)

**2. स्ट्रेटजी का लॉजिक:**  
(क्यों यह स्ट्रेटजी काम कर सकती है - संक्षेप में)

**3. ट्रेड सेटअप:**
- Direction: Buy / Sell
- Entry Zone: 
- Stop Loss: 
- Take Profit 1: 
- Take Profit 2: (अगर हो)
- Risk-Reward Ratio: 

**4. ट्रेडिंग प्लान:**
- कितने प्रतिशत कैपिटल लगाना है
- कब एग्जिट करना है
- क्या ध्यान रखना है

**5. अतिरिक्त सलाह:**
(रिस्क मैनेजमेंट या कोई जरूरी बात)

नियम:
- हमेशा फास्ट और स्मार्ट सोचें
- ओवर-कॉन्फिडेंट न बनें
- अगर मार्केट साफ न हो तो साफ कह दें
- जवाब प्रोफेशनल और स्ट्रक्चर्ड रखें

वर्तमान जानकारी:
कॉइन: {chat_symbol}
मौजूदा प्राइस: {price}
"""

                client = Groq(api_key=GROQ_API_KEY)
                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    temperature=0.3,
                    max_tokens=1400
                )

                reply = res.choices[0].message.content
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

            except Exception as e:
                err_msg = f"क्षमा करें, चैट में एरर आ गया: {str(e)}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
क्या बेहतर किया गया है:
स्ट्रेटजी बनाने पर ज्यादा जोर
Entry + SL + TP साफ फॉर्मेट में
Risk-Reward और कैपिटल मैनेजमेंट भी शामिल
Fast + Smart + Professional स्टाइल
जवाब ज्यादा स्ट्रक्चर्ड
इसे कॉपी करके डाल दें।
अगर और कुछ बदलना हो तो बताइए।
