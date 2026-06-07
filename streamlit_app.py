    #import streamlitimport os
import io
import asyncio
import time
import google.generativeai as genai
import edge_tts
from pydub import AudioSegment

st.set_page_config(page_title="The K2 TTS Studio", page_icon="🪖", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1 { color: #ffcc00 !important; font-family: 'Courier New', monospace; text-shadow: 2px 2px #002244; text-align: center; }
    .stButton>button { background-color: #002244 !important; color: #ffcc00 !important; border: 2px solid #ffcc00 !important; font-weight: bold; width: 100%; }
    .stButton>button:hover { background-color: #ffcc00 !important; color: #0d1117 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🪖 THE K2 — PREMIUM MYANMAR TTS")
st.write("---")

text_input = st.text_area("မြန်မာစာသား ထည့်ရန် (အများဆုံး စာလုံးရေ ၁၀,०००):", height=250, placeholder="ဒီနေရာမှာ အသံပြောင်းချင်တဲ့ မြန်မာစာတွေကို ရိုက်ထည့်ပါ...")
char_count = len(text_input)
st.write(f"✍️ လက်ရှိစာလုံးရေ: {char_count} / 10,000")

st.sidebar.header("🛠️ MISSION CONTROL")
engine_choice = st.sidebar.selectbox("TTS Engine ရွေးချယ်ရန်", ["Standard Edge-TTS (No Key Needed)", "Google AI Studio (Gemini)"])

if engine_choice == "Standard Edge-TTS (No Key Needed)":
    voice_option = st.sidebar.selectbox("မြန်မာအသံ ရွေးရန်", ["Thiha (သီဟ — Male)", "Nilar (နီလာ — Female)"])
    style_instruction = ""
else:
    voice_option = st.sidebar.selectbox("Gemini AI Voice ရွေးရန်", ["Puck (Upbeat Male)", "Charon", "Kore", "Fenrir", "Aoede"])
    style_instruction = st.sidebar.text_input("အသံနေအသံထား ခိုင်းရန်", "ပုံပြင်ပြောသလို အေးအေးဆေးဆေး ပြောပေးပါ")

async def generate_edge_tts(text, voice_name):
    voice_str = "my-MM-ThihaNeural" if "Thiha" in voice_name else "my-MM-NilarNeural"
    communicate = edge_tts.Communicate(text, voice_str)
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_bytes += chunk["data"]
    return audio_bytes

def generate_gemini_tts(text, voice_name, style):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: raise Exception("Advanced settings ထဲမှာ GEMINI_API_KEY ထည့်သွင်းပေးရန် လိုအပ်ပါသည်။")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"Please read the following Myanmar text out loud. Voice style instruction: {style}. Text: {text}"
    response = model.generate_content(prompt, config=genai.types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=genai.types.SpeechConfig(voice_config=genai.types.VoiceConfig(prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(voice_name=voice_name.split()[0].lower())))))
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("audio/"): return part.inline_data.data
    raise Exception("AI ထံမှ အသံဖိုင် တုံ့ပြန်မှု မရရှိပါ။")

if st.button("EXECUTE MISSION — GENERATE AUDIO! 🎯"):
    if not text_input.strip():
        st.warning("ကျေးဇူးပြု၍ စာသားတစ်ခုခု အရင်ရိုက်ထည့်ပါဗျာ။")
    else:
        try:
            status_box = st.status("⏳ စစ်ဆင်ရေးစတင်နေပြီ...")
            chunk_size = 2000
            chunks = [text_input[i:i+chunk_size] for i in range(0, len(text_input), chunk_size)]
            combined_audio = AudioSegment.empty()
            srt_content = ""
            cumulative_time_ms = 0
            
            for index, chunk in enumerate(chunks):
                status_box.update(label=f"⏳ အပိုင်း ({index+1}/{len(chunks)}) ကို အသံပြောင်းနေသည်...", state="running")
                if engine_choice == "Standard Edge-TTS (No Key Needed)":
                    chunk_bytes = asyncio.run(generate_edge_tts(chunk, voice_option))
                else:
                    chunk_bytes = generate_gemini_tts(chunk, voice_option, style_instruction)
                    time.sleep(1.0)
                
                chunk_audio = AudioSegment.from_file(io.BytesIO(chunk_bytes))
                combined_audio += chunk_audio
                duration_ms = len(chunk_audio)
                
                def format_srt_time(ms):
                    h = ms // 3600000
                    m = (ms % 3600000) // 60000
                    s = (ms % 60000) // 1000
                    mmm = ms % 1000
                    return f"{h:02d}:{m:02d}:{s:02d},{mmm:03d}"
                
                start_time_str = format_srt_time(cumulative_time_ms)
                cumulative_time_ms += duration_ms
                end_time_str = format_srt_time(cumulative_time_ms)
                srt_content += f"{index + 1}\n{start_time_str} --> {end_time_str}\n{chunk}\n\n"
            
            status_box.update(label="✅ အောင်မြင်သည်!", state="complete")
            output_buffer = io.BytesIO()
            combined_audio.export(output_buffer, format="mp3")
            final_audio_bytes = output_buffer.getvalue()
            
            st.audio(final_audio_bytes, format="audio/mp3")
            col1, col2 = st.columns(2)
            with col1: st.download_button("📥 Download MP3 Audio", data=final_audio_bytes, file_name="the_k2_audio.mp3", mime="audio/mp3")
            with col2: st.download_button("📥 Download SRT Subtitles", data=srt_content, file_name="the_k2_subtitles.srt", mime="text/plain")
        except Exception as e:
            st.error("❌ Error ဖြစ်ပွားခဲ့ပါသည်။")
            st.exception(e)
                                          - GDP for 1962
    # - ...
    # - GDP for 2022
    #
    # ...but I want this instead:
    # - Country Name
    # - Country Code
    # - Year
    # - GDP
    #
    # So let's pivot all those year-columns into two: Year and GDP
    gdp_df = raw_gdp_df.melt(
        ['Country Code'],
        [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
        'Year',
        'GDP',
    )

    # Convert years from string to integers
    gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])

    return gdp_df

gdp_df = get_gdp_data()

# -----------------------------------------------------------------------------
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# :earth_americas: GDP dashboard

Browse GDP data from the [World Bank Open Data](https://data.worldbank.org/) website. As you'll
notice, the data only goes to 2022 right now, and datapoints for certain years are often missing.
But it's otherwise a great (and did I mention _free_?) source of data.
'''

# Add some spacing
''
''

min_value = gdp_df['Year'].min()
max_value = gdp_df['Year'].max()

from_year, to_year = st.slider(
    'Which years are you interested in?',
    min_value=min_value,
    max_value=max_value,
    value=[min_value, max_value])

countries = gdp_df['Country Code'].unique()

if not len(countries):
    st.warning("Select at least one country")

selected_countries = st.multiselect(
    'Which countries would you like to view?',
    countries,
    ['DEU', 'FRA', 'GBR', 'BRA', 'MEX', 'JPN'])

''
''
''

# Filter the data
filtered_gdp_df = gdp_df[
    (gdp_df['Country Code'].isin(selected_countries))
    & (gdp_df['Year'] <= to_year)
    & (from_year <= gdp_df['Year'])
]

st.header('GDP over time', divider='gray')

''

st.line_chart(
    filtered_gdp_df,
    x='Year',
    y='GDP',
    color='Country Code',
)

''
''


first_year = gdp_df[gdp_df['Year'] == from_year]
last_year = gdp_df[gdp_df['Year'] == to_year]

st.header(f'GDP in {to_year}', divider='gray')

''

cols = st.columns(4)

for i, country in enumerate(selected_countries):
    col = cols[i % len(cols)]

    with col:
        first_gdp = first_year[first_year['Country Code'] == country]['GDP'].iat[0] / 1000000000
        last_gdp = last_year[last_year['Country Code'] == country]['GDP'].iat[0] / 1000000000

        if math.isnan(first_gdp):
            growth = 'n/a'
            delta_color = 'off'
        else:
            growth = f'{last_gdp / first_gdp:,.2f}x'
            delta_color = 'normal'

        st.metric(
            label=f'{country} GDP',
            value=f'{last_gdp:,.0f}B',
            delta=growth,
            delta_color=delta_color
        )
