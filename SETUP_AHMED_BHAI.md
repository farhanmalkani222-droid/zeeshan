# Ahmed bhai ke liye setup guide (Hawa Taps Instagram bot)

Ye bot Instagram ke official system se kaam karta hai, isliye account ban hone ka khatra nahi hai.

## Step 1: Instagram account Business banao
1. Instagram app kholo > Profile > Settings > **Account type and tools**.
2. **Switch to professional account** > Business chuno.

## Step 2: Meta developer app banao
1. Computer pe **developers.facebook.com** kholo, apne Facebook se login karo.
2. **My Apps > Create App** > type **Business** chuno, naam do "Hawa Taps Bot".
3. App ke andar **Add Product > Instagram** > **API setup with Instagram login** chuno.
4. **Add account** pe click karke @hawa_taps_ jodo.
5. Wahan **Generate token** dabao. Permission mein `instagram_business_basic` aur `instagram_business_manage_messages` dena. Jo token mile use copy karke save karo. Wo **IG_TOKEN** hai.
6. Wahin dikhne wala **Instagram account ID** copy karo. Wo **IG_ID** hai.
7. **App settings > Basic** mein **App secret** (Show dabao) copy karo. Wo **APP_SECRET** hai.
8. Ek koi bhi secret shabd sochlo, jaise `hawa-secret-786`. Wo **VERIFY_TOKEN** hai.

Ye 4 cheezein (IG_TOKEN, IG_ID, APP_SECRET, VERIFY_TOKEN) kisi ko public mat dena.

## Step 3: Bot ko internet pe chalao
Ye kaam Farhan bhai ya koi tech wala kar dega. Railway, Render ya kisi VPS pe:
- Repo deploy karo (Dockerfile ready hai).
- Upar wali 4 cheezein Environment Variables mein daalo. Chahein toh `ANTHROPIC_API_KEY` bhi (jab bot ko FAQ mein jawab na mile).
- `/data` ke liye persistent disk lagao, taaki restart pe chat history na jaaye.
- Deploy hone ke baad ek HTTPS link milega, jaise `https://hawa-bot.example.com`.

## Step 4: Webhook jodo
1. Meta dashboard > Instagram > **Webhooks** (Configure).
2. **Callback URL**: upar wala HTTPS link. **Verify token**: apna VERIFY_TOKEN.
3. **Verify and save** dabao. Phir **messages** pe Subscribe karo.

## Step 5: Instagram app mein permission
Instagram app > Settings > **Messages and story replies** > **Message controls** (ya Connected tools) mein "Allow access to messages" ON karo.

## Step 6: Test karo
Kisi dusre Instagram account se @hawa_taps_ ko "Assalam-o-alaikum" bhejo. 4 messages aane chahiye (salam + ₹300, office/factory, warranty, material).
Test ke waqt dusra account app mein **Roles > Instagram Testers** mein add hona chahiye.

## Step 7: Sabke liye live karo
Bina App Review ke bot sirf tester accounts ko reply karta hai. Live karne ke liye:
1. Meta dashboard > **App Review > Permissions and Features**.
2. `instagram_business_manage_messages` ke liye **Request advanced access** karo. Privacy policy ka link aur ek chhoti screen recording maangte hain (DM aane par bot ka reply dikhao).
3. Approval mein kuch din lag sakte hain. Phir app ko **Live** mode mein daalo.

## Roz ka istemal
- **Aap khud reply karo** toh bot us customer ke liye chup ho jaata hai. Bas Instagram app se normal reply kar do.
- Customer 3 ghante chup rahe toh bot ek baar follow-up bhejta hai.
- Photo ya voice note aaye toh bot bolta hai "Ahmed bhai dekh kar reply karenge". Us par aap khud reply karo.
- Jawab, daam ya address badalna ho toh `config.json` aur `faq.json` badlo, phir bot restart karo.

## Aap se ye chahiye
- Kin shehron mein pehle maal ja chuka hai (rapport line ke liye).
- COD hai ya nahi, delivery kitne din mein.
- 15-20 asli chat ke sample, taaki bot ka andaaz bilkul aapke jaisa ho.
