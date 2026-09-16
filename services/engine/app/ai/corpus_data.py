from __future__ import annotations

# Prose documents wrap poorly at 100 columns.
# ruff: noqa: E501

# Team-written welfare notes. Frontmatter is added when files are written.

DOCS: list[dict[str, str]] = [
    {
        "id": "sleep-rotating",
        "title_en": "Sleep on rotating shifts",
        "title_hi": "घूमती ड्यूटी पर नींद",
        "en": (
            "Rotating shifts can leave sleep feeling broken. Protect a dark, quiet block after night duty, "
            "even if it is shorter than a full night. Tell your roommate you are sleeping. Avoid bright screens "
            "in the last twenty minutes. If sleep will not come, get up, sit quietly, and try again. "
            "Saathi can open a sleep planner. A welfare officer can help if roster rest keeps slipping."
        ),
        "hi": (
            "घूमती ड्यूटी पर नींद टूट सकती है. रात की ड्यूटी के बाद अँधेरा और शांत समय रखें, भले वह पूरी रात न हो. "
            "रूममेट से कह दें कि आप सो रहे हैं. सोने से पहले स्क्रीन कम करें. नींद न आए तो उठकर चुपचाप बैठें, फिर कोशिश करें. "
            "साथी स्लीप प्लानर खोल सकता है. अगर आराम बार-बार कटता है तो कल्याण अधिकारी मदद कर सकते हैं."
        ),
    },
    {
        "id": "tactical-napping",
        "title_en": "Tactical napping",
        "title_hi": "छोटी झपकी",
        "en": (
            "A short nap of ten to twenty minutes can take the edge off before a long stretch of duty. "
            "Set an alarm. Sit or lie somewhere you will be found if needed. After the nap, stand, drink water, "
            "and give yourself a few minutes before you start work. Naps do not replace a rest day."
        ),
        "hi": (
            "दस से बीस मिनट की छोटी झपकी लंबी ड्यूटी से पहले थकान कम कर सकती है. अलार्म लगाएँ. "
            "ऐसी जगह लेटें जहाँ जरूरत हो तो आपको जगाया जा सके. झपकी के बाद खड़े हों, पानी पिएँ, फिर काम शुरू करें. "
            "झपकी आराम के दिन की जगह नहीं लेती."
        ),
    },
    {
        "id": "recovering-night-duty",
        "title_en": "Recovering after night duty",
        "title_hi": "रात की ड्यूटी के बाद वापसी",
        "en": (
            "After a night stretch, eat something simple, dim the light, and delay heavy talk if you can. "
            "Caffeine late in the morning can steal the next sleep. If you feel low or snappy, that can be tiredness. "
            "Ask for a quiet hour. If this pattern lasts many days, tell someone you trust or use check-in."
        ),
        "hi": (
            "रात की ड्यूटी के बाद सादा खाना लें, रोशनी कम करें, और भारी बातचीत थोड़ी देर टाल दें. "
            "सुबह देर तक चाय-कॉफी अगली नींद काट सकती है. चिड़चिड़ाहट थकान से भी आती है. "
            "एक शांत घंटा माँगें. अगर यह कई दिन चले तो किसी भरोसे वाले से कहें या चेक-इन करें."
        ),
    },
    {
        "id": "caffeine-timing",
        "title_en": "Caffeine timing",
        "title_hi": "चाय-कॉफी का समय",
        "en": (
            "Tea and coffee can help at the start of a night stretch. They work against you if you drink them "
            "close to the sleep you still need. Try a cut-off six hours before you plan to sleep. Water and a short walk "
            "often help as much in the last hours of duty."
        ),
        "hi": (
            "रात की ड्यूटी की शुरुआत में चाय-कॉफी मदद कर सकती है. सोने के करीब पीने से नींद कटती है. "
            "सोने से लगभग छह घंटे पहले बंद करने की कोशिश करें. ड्यूटी के आखिरी घंटों में पानी और छोटी सैर भी मदद करती है."
        ),
    },
    {
        "id": "box-breathing",
        "title_en": "Box breathing",
        "title_hi": "बॉक्स साँस",
        "en": (
            "Sit with both feet on the floor. Breathe in for four, hold for four, out for four, hold for four. "
            "Repeat four rounds. If you feel dizzy, stop and breathe normally. This is a way to settle the body, "
            "not a treatment. The toolkit has a guided ring if you prefer audio."
        ),
        "hi": (
            "दोनों पाँव जमीन पर रख कर बैठें. चार गिनती साँस अंदर, चार रोकें, चार बाहर, चार रोकें. "
            "चार बार दोहराएँ. चक्कर आए तो रोक दें. यह शरीर को शांत करने का एक तरीका है, इलाज नहीं. "
            "टूलकिट में गाइडेड रिंग भी है."
        ),
    },
    {
        "id": "grounding",
        "title_en": "Grounding",
        "title_hi": "ज़मीन से जुड़ना",
        "en": (
            "Name five things you can see, four you can feel, three you can hear, two you can smell, one you can taste. "
            "Feel your heels on the floor. This can help when thoughts race after a hard shift. "
            "If the feeling does not ease, ask a person to sit with you."
        ),
        "hi": (
            "पाँच चीजें देखें, चार महसूस करें, तीन सुनें, दो सूँघें, एक स्वाद लें. एड़ी ज़मीन पर महसूस करें. "
            "कठिन शिफ्ट के बाद विचार दौड़ें तो यह मदद कर सकता है. अगर राहत न मिले तो किसी से पास बैठने को कहें."
        ),
    },
    {
        "id": "anger-hard-day",
        "title_en": "Anger after a hard day",
        "title_hi": "कठिन दिन के बाद गुस्सा",
        "en": (
            "Anger after a long duty is common. Step away if you can. Cool water on the wrists, a slow walk around the block, "
            "or writing one sentence in your journal can take the heat down. Do not take it out on family on a call. "
            "A counsellor conversation is available if anger keeps coming back."
        ),
        "hi": (
            "लंबी ड्यूटी के बाद गुस्सा आना आम है. हो सके तो थोड़ी दूर हटें. कलाई पर ठंडा पानी, धीमी सैर, "
            "या जर्नल में एक वाक्य गर्मी कम कर सकता है. फोन पर परिवार पर न निकालें. "
            "अगर गुस्सा बार-बार आए तो परामर्श बातचीत उपलब्ध है."
        ),
    },
    {
        "id": "family-long-deployment",
        "title_en": "Talking to family during long deployments",
        "title_hi": "लंबी तैनाती पर परिवार से बात",
        "en": (
            "Short, regular calls often land better than one long exhausted call. Say what you can share. "
            "It is all right to say you are tired and will talk tomorrow. Ask one question about home. "
            "If time zones or roster make this hard, write a voice note when you are calmer."
        ),
        "hi": (
            "थकी हुई एक लंबी कॉल से नियमित छोटी कॉल बेहतर बैठती है. जो कह सकते हैं कहें. "
            "यह कहना ठीक है कि आप थके हैं और कल बात करेंगे. घर के बारे में एक सवाल पूछें. "
            "रोस्टर कठिन हो तो शांत समय पर वॉइस नोट भेजें."
        ),
    },
    {
        "id": "children-from-far",
        "title_en": "Staying close to children from far away",
        "title_hi": "दूर से बच्चों के करीब रहना",
        "en": (
            "A small ritual helps: the same goodnight line, a drawing exchanged, or a weekly story. "
            "Keep promises small so you can keep them. If a call is missed, send a short note later. "
            "You do not have to explain the whole posting to a child."
        ),
        "hi": (
            "छोटी आदत मदद करती है: वही गुडनाइट लाइन, एक चित्र, या साप्ताहिक कहानी. "
            "वादा छोटा रखें ताकि निभा सकें. कॉल छूट जाए तो बाद में छोटा संदेश भेजें. "
            "बच्चे को पूरी पोस्टिंग समझाने की जरूरत नहीं."
        ),
    },
    {
        "id": "welfare-conversation",
        "title_en": "What a welfare conversation is",
        "title_hi": "कल्याण बातचीत क्या है",
        "en": (
            "A welfare conversation is a practical talk with an officer about rest, leave, pay, family, or strain. "
            "It is not a punishment parade. You can ask for time, a referral, or help with paperwork. "
            "You can also say you do not want to talk today. Saathi can offer contact when you ask."
        ),
        "hi": (
            "कल्याण बातचीत आराम, छुट्टी, वेतन, परिवार या दबाव पर अधिकारी से व्यावहारिक बात है. "
            "यह सजा नहीं है. समय, रेफरल, या कागज़ों में मदद माँग सकते हैं. "
            "आज न बोलने का अधिकार भी है. पूछने पर साथी संपर्क दे सकता है."
        ),
    },
    {
        "id": "what-counsellors-do",
        "title_en": "What counsellors do",
        "title_hi": "परामर्शदाता क्या करते हैं",
        "en": (
            "A counsellor is a trained listener. Sessions are for you to talk about what is heavy, at your pace. "
            "They do not command your unit and they do not set your tier. "
            "If you want a session, Saathi can offer human contact. You can stop a session at any time."
        ),
        "hi": (
            "परामर्शदाता प्रशिक्षित श्रोता हैं. सत्र आपकी गति पर भारी बातों के लिए है. "
            "वे यूनिट नहीं चलाते और टियर तय नहीं करते. "
            "सत्र चाहिए तो साथी संपर्क दे सकता है. आप कभी भी सत्र रोक सकते हैं."
        ),
    },
    {
        "id": "how-manobal-uses-data",
        "title_en": "How MANOBAL uses your data",
        "title_hi": "MANOBAL आपका डेटा कैसे इस्तेमाल करता है",
        "en": (
            "Check-ins and roster patterns stay in the system to notice strain early. Officers see cases, not a ranked list of people. "
            "Command sees unit totals only. Audio from a voice turn is cleared after features are taken, if you consented. "
            "You can see who accessed your file in Me. You can withdraw a consent."
        ),
        "hi": (
            "चेक-इन और रोस्टर पैटर्न दबाव जल्दी दिखाने के लिए रहते हैं. अधिकारी केस देखते हैं, लोगों की रैंक सूची नहीं. "
            "कमांड केवल यूनिट योग देखता है. सहमति हो तो आवाज़ की फाइल फीचर के बाद मिटती है. "
            "मी में देख सकते हैं किसने फाइल देखी. सहमति वापस भी ले सकते हैं."
        ),
    },
    {
        "id": "one-safety-exception",
        "title_en": "The one safety exception",
        "title_hi": "एक सुरक्षा अपवाद",
        "en": (
            "Saathi does not promise that nobody will ever know. If you are in immediate danger, the safety path asks a welfare "
            "and medical officer to reach you. That is the one exception, so someone can help in time. "
            "Ordinary check-ins do not open that path."
        ),
        "hi": (
            "साथी यह वादा नहीं करता कि कोई कभी नहीं जानेगा. अगर आप तुरंत खतरे में हों, तो सुरक्षा पथ कल्याण "
            "और चिकित्सा अधिकारी से संपर्क करवाता है. यही एक अपवाद है, ताकि समय पर मदद मिल सके. "
            "सामान्य चेक-इन यह पथ नहीं खोलते."
        ),
    },
    {
        "id": "leave-planning",
        "title_en": "Leave planning",
        "title_hi": "छुट्टी की योजना",
        "en": (
            "Write the dates you need and why in one line. Check clashes with unit events if you know them. "
            "Ask early. If leave is delayed, a welfare officer can help chase the paper. "
            "Saathi can open a leave planner. Do not argue the decision with Saathi."
        ),
        "hi": (
            "जरूरी तारीख और एक पंक्ति में कारण लिखें. यूनिट कार्यक्रम से टकराव हो तो देख लें. "
            "जल्दी माँगें. छुट्टी अटके तो कल्याण अधिकारी कागज़ आगे बढ़ा सकते हैं. "
            "साथी लीव प्लानर खोल सकता है. फैसले पर साथी से बहस न करें."
        ),
    },
    {
        "id": "return-from-leave",
        "title_en": "Return from leave",
        "title_hi": "छुट्टी से वापसी",
        "en": (
            "The first days back can feel jarring. Sleep may be off. Give yourself a quieter first evening if roster allows. "
            "Tell a buddy if home was hard. A short check-in helps the system notice the change without a long story."
        ),
        "hi": (
            "वापसी के पहले दिन अटपटे लग सकते हैं. नींद उखड़ सकती है. रोस्टर हो तो पहली शाम शांत रखें. "
            "घर कठिन रहा हो तो बडी से कहें. छोटा चेक-इन लंबी कहानी बिना बदलाव दिखा देता है."
        ),
    },
    {
        "id": "new-posting",
        "title_en": "Starting in a new posting",
        "title_hi": "नई पोस्टिंग की शुरुआत",
        "en": (
            "New rooms, new names, new roster. Learn one route, one mess time, and one person you can ask a plain question. "
            "It is normal to feel out of place for a few weeks. The toolkit has a settling piece. "
            "A welfare conversation can help with admin that is stuck."
        ),
        "hi": (
            "नया कमरा, नए नाम, नया रोस्टर. एक रास्ता, एक मेस समय, और एक व्यक्ति याद करें जिससे सादा सवाल पूछ सकें. "
            "कुछ हफ्ते अटपटा लगना सामान्य है. टूलकिट में बसने वाली सामग्री है. "
            "अटके काम के लिए कल्याण बातचीत मदद कर सकती है."
        ),
    },
    {
        "id": "money-stress",
        "title_en": "Money stress basics",
        "title_hi": "पैसे की चिंता की बुनियाद",
        "en": (
            "List what must be paid this month and what can wait. If a loan or family demand is heavy, a welfare officer can "
            "point to unit support and legal aid where it exists. Do not send money on a threat. "
            "Saathi will not manage your accounts."
        ),
        "hi": (
            "इस महीने क्या जरूरी है और क्या रुक सकता है, लिखें. कर्ज या घर की माँग भारी हो तो कल्याण अधिकारी "
            "यूनिट मदद और जहाँ हो कानूनी सहायता बता सकते हैं. धमकी पर पैसे न भेजें. "
            "साथी आपके खाते नहीं चलाता."
        ),
    },
    {
        "id": "land-dispute-legal-aid",
        "title_en": "Land or property dispute and legal aid",
        "title_hi": "जमीन विवाद और कानूनी सहायता",
        "en": (
            "Keep copies of papers. Do not travel alone to a tense site if you can avoid it. "
            "Ask welfare for the legal aid desk your force uses. A counsellor can help with the strain while the case moves. "
            "Saathi cannot give legal advice."
        ),
        "hi": (
            "कागज़ों की प्रति रखें. तनाव वाली जगह अकेले न जाएँ अगर बच सकें. "
            "बल की कानूनी सहायता डेस्क के लिए कल्याण से पूछें. केस चलते तनाव के लिए परामर्श मदद कर सकता है. "
            "साथी कानूनी सलाह नहीं देता."
        ),
    },
    {
        "id": "alcohol-and-sleep",
        "title_en": "Alcohol and sleep",
        "title_hi": "शराब और नींद",
        "en": (
            "A drink can make you sleepy and then break sleep later in the night. If you are using alcohol to come down after duty, "
            "that pattern is worth a honest check-in. Help is available without lecture. "
            "Medical and counselling paths exist if you want them."
        ),
        "hi": (
            "एक पेग नींद ला सकता है और रात में नींद तोड़ भी सकता है. ड्यूटी के बाद उतरने के लिए शराब बन गई हो "
            "तो ईमानदार चेक-इन ठीक है. बिना लेक्चर मदद मिल सकती है. "
            "चाहें तो चिकित्सा और परामर्श पथ हैं."
        ),
    },
    {
        "id": "after-critical-incident",
        "title_en": "After a critical incident",
        "title_hi": "गंभीर घटना के बाद",
        "en": (
            "After a hard incident, eat, drink water, and stay with people if you can. Sleep may be strange. "
            "You do not have to tell the story. Psychological first aid is practical care, not an interview. "
            "Ask-to-talk cards may appear for a few days. You can say no."
        ),
        "hi": (
            "कठिन घटना के बाद खाएँ, पानी पिएँ, और हो सके तो लोगों के साथ रहें. नींद अजीब हो सकती है. "
            "कहानी बतानी जरूरी नहीं. व्यावहारिक देखभाल है, पूछताछ नहीं. "
            "कुछ दिन बात करने के कार्ड आ सकते हैं. ना कह सकते हैं."
        ),
    },
    {
        "id": "grief",
        "title_en": "Grief",
        "title_hi": "शोक",
        "en": (
            "Grief can come in waves during duty. Eat, rest when you can, and tell one person what you need this week. "
            "Rituals that matter to you are yours. A counsellor can sit with the weight. "
            "Leave for a death in the family is a welfare matter, not a favour."
        ),
        "hi": (
            "ड्यूटी के दौरान शोक लहरों में आ सकता है. खाएँ, जब हो आराम करें, और इस हफ्ते क्या चाहिए एक व्यक्ति से कहें. "
            "जो रीति आपको चाहिए वह आपकी है. परामर्शदाता इस बोझ के साथ बैठ सकते हैं. "
            "परिवार में मृत्यु पर छुट्टी कल्याण विषय है, एहसान नहीं."
        ),
    },
    {
        "id": "colleague-conflict",
        "title_en": "Conflict with a colleague",
        "title_hi": "साथियों से टकराव",
        "en": (
            "Cool down before you speak. Describe the task, not the person. If it is unsafe or bullying, take it to welfare "
            "rather than letting it sit. Saathi will not take sides or name other personnel."
        ),
        "hi": (
            "बोलने से पहले शांत हों. काम बताएँ, व्यक्ति नहीं. असुरक्षित या बदमाशी हो तो कल्याण तक ले जाएँ. "
            "साथी पक्ष नहीं लेता और दूसरे जवान का नाम नहीं लेता."
        ),
    },
    {
        "id": "heat-cold-stress",
        "title_en": "Heat and cold stress basics",
        "title_hi": "गर्मी और ठंड का दबाव",
        "en": (
            "In heat, drink water before you feel very thirsty, rest in shade when allowed, and say if you feel faint. "
            "In cold, keep dry layers and cover the head and hands. These are body basics, not a test of toughness. "
            "Tell a buddy if something feels wrong."
        ),
        "hi": (
            "गर्मी में प्यास तेज होने से पहले पानी पिएँ, छाया में आराम करें, और चक्कर हो तो कहें. "
            "ठंड में सूखी परतें रखें, सिर और हाथ ढकें. यह शरीर की बुनियाद है, हिम्मत की परीक्षा नहीं. "
            "कुछ गलत लगे तो बडी से कहें."
        ),
    },
    {
        "id": "loneliness",
        "title_en": "Loneliness",
        "title_hi": "अकेलापन",
        "en": (
            "Barracks can be full and still feel empty. A short tea with a buddy, a call home, or a walk after duty can help. "
            "If the empty feeling stays, a counsellor conversation is a fair next step. "
            "You do not have to wait until it is unbearable."
        ),
        "hi": (
            "बैरक भरा हो और फिर भी खाली लगे. बडी के साथ चाय, घर पर कॉल, या ड्यूटी के बाद सैर मदद कर सकती है. "
            "खालीपन टिका रहे तो परामर्श बातचीत ठीक अगला कदम है. "
            "असहनीय होने तक इंतजार जरूरी नहीं."
        ),
    },
    {
        "id": "being-a-buddy",
        "title_en": "Being a buddy",
        "title_hi": "बडी बनना",
        "en": (
            "A good buddy notices quiet changes: missed meals, no jokes, long stares at the phone. Ask once, plainly. "
            "You do not have to fix it. Offer to walk with them to welfare or to sit while they check in. "
            "If they are in immediate danger, use the safety path."
        ),
        "hi": (
            "अच्छा बडी शांत बदलाव देखता है: छूटा खाना, मजाक न होना, फोन पर लंबी निगाह. एक बार साफ पूछें. "
            "आपको ठीक करना नहीं है. कल्याण तक साथ चलने या चेक-इन तक बैठने को कहें. "
            "तुरंत खतरा हो तो सुरक्षा पथ इस्तेमाल करें."
        ),
    },
    {
        "id": "festival-duty-rest",
        "title_en": "Festival duty and rest",
        "title_hi": "त्योहार की ड्यूटी और आराम",
        "en": (
            "Festival duty can sting when home is far. Plan one small thing you can actually do: a call, a sweet from the mess, a quiet ten minutes. "
            "Ask about rest after the event. You do not have to explain your faith, or the lack of it, to anyone."
        ),
        "hi": (
            "घर दूर हो तो त्योहार की ड्यूटी चुभ सकती है. एक छोटी चीज तय करें जो हो सके: कॉल, मेस से मिठाई, दस शांत मिनट. "
            "आयोजन के बाद आराम के बारे में पूछें. आस्था या उसके न होने का हिसाब किसी को देना जरूरी नहीं."
        ),
    },
    {
        "id": "barracks-rest",
        "title_en": "Rest in shared barracks",
        "title_hi": "साझे बैरक में आराम",
        "en": (
            "Agree a quiet hour when someone is off a night stretch. Headphones help. If noise will not stop, ask the NCO "
            "for a practical shift of bunks rather than a fight. Sleep is a welfare issue."
        ),
        "hi": (
            "रात की ड्यूटी वाले के लिए शांत घंटा तय करें. हेडफोन मदद करते हैं. शोर न रुके तो झगड़े की जगह "
            "एनसीओ से बिस्तर बदलने को कहें. नींद कल्याण का विषय है."
        ),
    },
    {
        "id": "asking-rest-day",
        "title_en": "Asking for a short rest day",
        "title_hi": "छोटा आराम दिन माँगना",
        "en": (
            "If you have had many days on, a short rest request is allowed talk. Say how many days you have been on and what would help tomorrow. "
            "A welfare officer can carry REST_48H where it fits. Saathi cannot grant leave."
        ),
        "hi": (
            "कई दिन ड्यूटी हो तो छोटा आराम माँगना मना नहीं. कितने दिन लगे और कल क्या मदद करेगा, कहें. "
            "कल्याण अधिकारी जहाँ फिट हो REST_48H ले जा सकते हैं. साथी छुट्टी मंजूर नहीं करता."
        ),
    },
]
