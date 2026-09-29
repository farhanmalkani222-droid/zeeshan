# Ahmed bhai ke liye ManyChat guide (bina coding ke Instagram bot)

Ye tareeka Meta developer app ke bina chalta hai. Bas ManyChat pe Instagram jodna hai. Screen ke naam thode alag ho sakte hain, ManyChat unhe badalta rehta hai.

## Step 1: Pehle account safe karo
1. Instagram ka password badal do (naya, mazboot).
2. Instagram > Settings > Accounts Center > Password and security mein **Two-factor authentication** ON karo.
3. Account **Business** ya **Creator** hona chahiye (Settings > Account type and tools).

## Step 2: ManyChat pe Instagram jodo
1. **manychat.com** pe sign up karo, **Instagram** chuno.
2. **Connect Instagram** dabao. Instagram/Meta ka apna login screen khulega. Wahin login karo. Password kisi ko batana nahi hai.
3. Jo permissions maange, sab Allow karo.

## Step 3: Automation A, salam ka jawab
- Trigger: customer ke message mein ye shabd ho: `salam, assalam, assalamu, salaam, walaikum`
- Agar message mein `walaikum` hai toh shuru mein likho **"Assalam-o-alaikum!"**, warna **"Walaikum-assalam!"**
- Sirf ye bhejo: `[opener] Hawa Taps mein aapka swagat hai. Nal ke baare mein aapko kya jaanna hai?` (4 message yahan nahi bhejne).

## Step 4: Automation B, jab customer poori jaankari maange
- Trigger shabd: `details, info, inquiry, enquiry, moq`
- Tab hi ye 4 message bhejo (har customer ko sirf ek baar).
- `price, rate, kimat, kitne, kitna` par sirf price bhejo: Hamare taps ₹300 per tap hain. Kitne chahiye?
- Rule: customer jo poochhe sirf wahi batao. Nal ki poori jaankari tabhi do jab wo maange.

## Ye 4 message copy-paste karo
**Message 1:**
Walaikum-assalam! Hawa Taps mein aapka swagat hai. Ek nal ki keemat ₹300 hai. Courier ke zariye All India delivery ho jaati hai, jahan chahiye wahan.

**Message 2:**
Hamara head office Nagpada, Mumbai mein hai, factory Taloja, Mumbai mein hai. Maal courier ke zariye aap tak aa jaayega.

**Message 3:**
Nal pe 1 saal warranty. Uske baad bhi kuch hua toh kharab nal Ahmad bhai tak bhej dena, badle mein naya nal free of cost mil jayega inshallah.

**Message 4:**
Nal ABS material ka bana hai, saade plastic se 10 guna zyada mazboot, aur button aluminium ka hai, toh tootne ki koi shikayat nahi. Isse chhote models Amazon pe ₹350 aur ₹400 mein bikte hain, ye wale ki keemat ₹300 per nal hai.

(Agar customer ne "walaikum" likha ho toh Message 1 ke shuru mein "Assalam-o-alaikum!" likho.)

## Step 5: Automation C, aam sawaal
Har ek ke liye alag keyword reply banao:
- `size, inch` -> Naal half inch size ka hai.
- `strong, mazboot, weight` -> Humne 70kg ka aadmi naal pe khada kar diya, tab bhi naal nahi toota.
- `warranty, kharab, replace` -> Message 3 wala jawab.
- `kahan se, factory, origin` -> Hamara maal Taloja MIDC factory area se aata hai. Courier se All India delivery hoti hai.
- `paani, water saving` -> Ye taps 70-80% paani bachate hain, ek nal se roz kam-se-kam 60 litre ki bachat. 50,000+ masjids, 30,000+ madarse aur 1,000+ schools/hospitals mein use ho raha hai.

## Step 6: Default reply (jab kuch match na ho)
Likho: **Thoda detail bata dein, Ahmed bhai isko confirm karke jaldi reply karenge.**
Iske saath notification ON rakho, taaki aapko dikhe kis customer ko aapka jawab chahiye.

## Step 7: Follow-up
Message 4 ke baad **Smart Delay 3 ghante** lagao. Agar customer ne jawab nahi diya toh ye bhejo:
Hello! Aapne taps ke baare mein poocha tha. Koi aur sawaal ho ya order karna ho toh bata dein.

## Step 8: Test karo
Dusre Instagram account se @hawa_taps_ ko "Assalam-o-alaikum" bhejo. 4 message aane chahiye. Phir "price" bhejo aur "size kya hai" bhi.

## Dhyan rakhne ki baatein
- Spelling galat hone par bot default reply dega. Aap khud jawab de dena.
- Ajeeb sawaalon ka jawab bot nahi dega, aapko dena hoga.
- Aap khud reply karo toh ManyChat mein us chat ko **pause automation** ya live chat mode mein daalo, warna bot bhi bolta rahega.
- ManyChat ka free plan limited hai. Paid plan ka daam unki website pe dekh lena.
- Baad mein zyada control chahiye toh humara Python bot (`SETUP_AHMED_BHAI.md`) bhi tayyar hai.
