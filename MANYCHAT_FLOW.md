# Hawa Taps: ManyChat flow (no-code alternative to the Python bot)

Written from how ManyChat generally works. Screen names and plan limits change, so check them in the app.

## 1. Connect
Sign up at manychat.com, choose Instagram, click "Connect Instagram" and log in on Meta's own screen. Turn on two-factor first.

## 2. Automation A: Salam (first greeting)
- Trigger: DM contains any of `salam, assalam, assalamu, salaam, walaikum`.
- Condition: if the message contains `walaikum`, opener is "Assalam-o-alaikum!". Otherwise "Walaikum-assalam!".
- Send the 4 messages below in order, with a 2-second Delay block between them.

## 3. Automation B: Price or inquiry
- Trigger keywords: `price, rate, kimat, keemat, kitne, kitna, cost, hi, hello, details, order, chahiye`.
- Same 4 messages. Set it to run once per customer so it does not repeat.

## The 4 messages
1. `[Walaikum-assalam! / Assalam-o-alaikum!] Hawa Taps mein aapka swagat hai. Ek nal ki keemat ₹300 hai. Courier ke zariye All India delivery ho jaati hai, jahan chahiye wahan.`
2. `Hamara head office Nagpada, Mumbai mein hai, factory Taloja, Mumbai mein hai. Maal courier ke zariye aap tak aa jaayega.`
3. `Nal pe 1 saal warranty. Uske baad bhi kuch hua toh kharab nal Ahmad bhai tak bhej dena, badle mein naya nal free of cost mil jayega inshallah.`
4. `Nal ABS material ka bana hai, saade plastic se 10 guna zyada mazboot, aur button aluminium ka hai, toh tootne ki koi shikayat nahi. Isse chhote models Amazon pe ₹350 aur ₹400 mein bikte hain, ye wale ki keemat ₹300 per nal hai.`

## 4. Automation C: Common questions (keyword replies)
- `size, inch`: "Naal half inch size ka hai."
- `strong, mazboot, weight`: "Humne 70kg ka aadmi naal pe khada kar diya, tab bhi naal nahi toota."
- `warranty, kharab, replace`: use message 3.
- `kahan se, factory, origin`: "Hamara maal Taloja MIDC factory area se aata hai. Courier se All India delivery hoti hai."
- `paani, water saving`: "Ye taps 70-80% paani bachate hain, ek nal se roz kam-se-kam 60 litre ki bachat. 50,000+ masjids, 30,000+ madarse aur 1,000+ schools/hospitals mein use ho raha hai."

## 5. Default reply
"Thoda detail bata dein, Ahmed bhai isko confirm karke jaldi reply karenge." Turn on the notification so Ahmed bhai sees these chats.

## 6. Follow-up
Smart Delay of 3 hours after message 4. If no reply, send: "Hello! Aapne taps ke baare mein poocha tha. Koi aur sawaal ho ya order karna ho toh bata dein."

## Limits
- Keyword matching is stricter than the Python bot; spelling mistakes may fall to the default reply.
- No AI answers for unusual questions.
- If Ahmed bhai replies manually, ManyChat may keep running automations unless he uses its pause or live chat option.
