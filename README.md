# Jose Alvarez Bot (Türkçe)

Telegram üzerinde çalışan, Türkçe konuşan bir ilişki-koçu botu. `/start` ile
karşılama mesajı ve üç konu butonu (Aşk / Aile / Arkadaşlık) gösterilir; konu
seçildikten sonra Claude API'si üzerinden destekleyici bir sohbet başlar.

## 1. Telegram bot token'ı alma

GitHub/Railway hesabına erişimin gitmiş olsa bile, bot token'ı senin Telegram
hesabına bağlı — GitHub ile ilgisi yok. İki seçeneğin var:

- **Eski botu kurtarmak istersen:** Telegram'da eski bot hesabına hâlâ
  erişimin varsa, @BotFather'a git → `/mybots` → botunu seç → **API Token** →
  **Revoke current token** ile yeni bir token üretebilirsin. Kullanıcı adı
  (`josealvarez10_bot`) aynı kalır.
- **Sıfırdan başlamak istersen:** @BotFather'a `/newbot` yaz, ismini ve
  kullanıcı adını belirle (adın sonu `bot` ile bitmeli, örn. `jose_alvarez_bot`).
  Sana bir token verecek, onu aşağıda kullanacaksın.

## 2. Gemini API anahtarı (ücretsiz)

1. https://aistudio.google.com adresine git, Google hesabınla giriş yap.
2. **Get API key** (veya **API anahtarı al**) butonuna tıkla, yeni bir proje
   seç/oluştur ve anahtarı oluştur.
3. Kredi kartı gerekmez. Ücretsiz katman `gemini-2.0-flash` modelinde günde
   yaklaşık 1.000–1.500 istek, dakikada ~15 istek civarında bir sınırla
   çalışır (Google zaman zaman bu sınırları değiştirebiliyor — güncel
   sınırları AI Studio panelinde görebilirsin).
4. Not: Ücretsiz katmanda gönderdiğin veriler Google'ın modellerini
   geliştirmek için kullanılabilir. Bot hassas/kişisel ilişki konuşmaları
   işlediği için bunu bilerek ilerle; istersen faturalandırmayı açıp bu
   veri kullanımını kapatabilirsin (ücretli katmanda bu kapanıyor).

## 3. Yerel test (opsiyonel)

```bash
pip install -r requirements.txt
cp .env.example .env
# .env dosyasını kendi token/anahtarlarınla doldur
export $(cat .env | xargs)   # ya da python-dotenv ekleyip bot.py başına
                              # `from dotenv import load_dotenv; load_dotenv()` ekle
python bot.py
```

## 4. Railway'e deploy

1. Bu klasörü yeni bir GitHub reposuna yükle (yeni bir GitHub hesabı/repo
   açman gerekecek, çünkü eskisine erişimin yok).
2. Railway'de **New Project → Deploy from GitHub repo** ile bu repoyu seç.
3. Railway **Variables** sekmesinden şunları ekle:
   - `TELEGRAM_BOT_TOKEN`
   - `GEMINI_API_KEY`
   - `GEMINI_MODEL` (opsiyonel, varsayılan `gemini-2.0-flash`)
4. Start command otomatik algılanmazsa: `python bot.py`
5. Deploy sonrası Telegram'da `/start` yazarak test et.

## Notlar / geliştirme fikirleri

- **Bellek kalıcı değil:** Şu an konuşma geçmişi sadece RAM'de tutuluyor,
  sunucu yeniden başlarsa (Railway redeploy, crash vb.) herkesin sohbet
  geçmişi sıfırlanır. Kalıcı hafıza istersen SQLite veya Postgres eklenebilir
  (Railway'de tek tıkla Postgres eklentisi var).
- **Güvenlik sınırı korunuyor:** Sistem promptunda, kullanıcı birine zarar
  verme/intikam alma planı isterse botun bunu reddedip duygusal desteğe
  yönlendirmesi sağlandı — eski botunda gördüğüm davranışla aynı. Bunu
  kaldırmanı önermem; hem kullanıcıları hem seni (operatör olarak) korur.
- **Satış senaryosu:** Alıcıya repo + Railway projesini devretmek istiyorsan,
  Railway projesini onun hesabına transfer edebilir ya da ortam
  değişkenlerini (`.env`) ona verip kendi Railway hesabında deploy etmesini
  sağlayabilirsin. Bot kullanıcı adını da devretmek istiyorsan @BotFather'dan
  `/mybots` → **Transfer Ownership** seçeneğini kullanabilirsin (Telegram bunu
  destekliyorsa; bazı sürümlerde token'ı doğrudan alıcıya vermek daha
  pratiktir).
- **Gemini anahtarı kimin olacak?** Ücretsiz katman olsa bile, kendi Google
  hesabınla ürettiğin anahtarı botta bırakırsan trafik/kota senin hesabından
  düşer. Kalıcı satışta alıcının kendi Google hesabından kendi anahtarını
  alıp Railway'e girmesi daha temiz bir ayrım sağlar.
