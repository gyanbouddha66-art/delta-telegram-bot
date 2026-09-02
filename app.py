with tab2:
    st.markdown("### 💬 GYAN AI Pro ट्रेडिंग मेंटर से सीधी बातचीत")
    st.markdown("यहाँ आप Universal Trading Institute के इस AI मेंटर से किसी भी कॉइन या अपनी ट्रेडिंग स्ट्रेटजी के बारे में हिंदी में चर्चा कर सकते हैं।")
    
    chat_symbol = st.selectbox("चैट के लिए सिंबल चुनें", symbols_list, key="t2_sym")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input("जैसे पूछें: 'इस कॉइन में फास्ट ट्रेड दो' या 'आज की बेस्ट स्केलपिंग स्ट्रेटजी बताओ'"):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("GYAN AI मेंटर जवाब तैयार कर रहा है..."):
                try:
                    ticker = get_ticker(chat_symbol)
                    price = ticker.get("mark_price", "N/A")

                    system_prompt = f"""
आप GYAN AI Pro के प्रोफेशनल Fast Trading और Scalping मेंटर हैं।
आप हमेशा शुद्ध हिंदी में जवाब देते हैं।

आपका तरीका हमेशा यह होना चाहिए:

1. पहले एक **साफ और स्मार्ट Fast Trading स्ट्रेटजी** बनाएं।
2. फिर उसी स्ट्रेटजी के अनुसार **ट्रेड सेटअप** दें।
3. Entry, Stop Loss (SL) और Take Profit (TP) जरूर बताएं।
4. ट्रेड Fast और Smart होना चाहिए (जल्दी प्रॉफिट वाला)।
5. जवाब प्रोफेशनल, स्ट्रक्चर्ड और आसान भाषा में दें।

जवाब का फॉर्मेट हमेशा इस तरह रखें:

**स्ट्रेटजी का नाम:**  
(यहाँ स्ट्रेटजी का नाम लिखें)

**स्ट्रेटजी का लॉजिक:**  
(संक्षेप में समझाएं)

**ट्रेड सेटअप:**
- Direction: Buy / Sell
- Entry: 
- Stop Loss: 
- Take Profit 1: 
- Take Profit 2: (अगर हो)
- Risk-Reward: 

**अतिरिक्त सलाह:**  
(रिस्क मैनेजमेंट या कोई जरूरी बात)

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
                        max_tokens=1300
                    )

                    reply = res.choices[0].message.content
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

                except Exception as e:
                    err_msg = f"क्षमा करें, चैट में एरर आ गया: {str(e)}"
                    st.error(err_msg)
                    st.session_state.messages.append({"role": "assistant", "content": err_msg})
