# Konuşma metni: Safe Cooperative Radiation Source Search

*`docs/Safe_Cooperative_Radiation_Source_Search_v3.pptx` için, toplam yaklaşık 11–12 dakika. Köşeli parantezli notlar sana; yüksek sesle okunmaz.*

---

## Slayt 1: Kapak (~30 sn)

Herkese merhaba, ben Nida. Bugün size tezimin ara aşamasını anlatacağım.

Bir an şunu düşünün: bir binanın içinde güçlü bir radyoaktif kaynak kaybolmuş. İçeri insan göndermek çok tehlikeli, o yüzden bir robot ekibi gönderiyoruz. Robotların görevi kaynağı bulmak. Ama burada bir sorun var: robotlar kaynağa yaklaştıkça hem daha iyi ölçüm yapıyorlar hem de daha fazla radyasyona maruz kalıyorlar. Radyasyon robotların elektroniğine zarar veriyor ve bu zarar birikiyor.

Tezimin sorusu tam olarak bu: **bir robot ekibi kaynağı bulurken, her robotun dışarı çıkabilecek kadar radyasyon bütçesini koruması nasıl sağlanır?**

Sağdaki görsel benim 3D simülatörümden. Zemindeki renk radyasyon şiddetini gösteriyor; kaynağa yaklaştıkça parlıyor.

---

## Slayt 2: Neden önemli (~1 dk)

Bu problem gerçek hayattan geliyor.

2017'de Fukushima Daiichi'nin 2 numaralı reaktöründe, ana robottan önce gönderilen bir temizlik robotunun kameraları yaklaşık iki saat sonra bozuldu ve robot geri çekilmek zorunda kaldı. Hemen ardından "Scorpion" adlı ana robot aynı reaktörde takılıp kaldı ve terk edildi.

Kaybolan veya çalınan radyoaktif kaynaklar da ciddi bir sorun. Uluslararası Atom Enerjisi Ajansı'nın veri tabanına göre yalnızca 2022 yılında, radyoaktif malzemeyle ilgili 146 yasa dışı veya izinsiz faaliyet olayı bildirilmiş.

Bu örneklerden çıkan ders şu: **bir robot, radyasyon bütçesi bitmeden dışarı çıkmalı.** Çıkamazsa hem robotu hem de topladığı bilgiyi kaybediyoruz.

---

## Slayt 3: Üç adımda problem (~1 dk)

Problemi üç adımda özetleyebilirim.

**Birinci adım, giriş.** Robotlar tek kapıdan odaya giriyor. Kaynağın nerede olduğunu da, ne kadar güçlü olduğunu da bilmiyoruz.

**İkinci adım, ölçüm.** Robotlar dağılıp radyasyon ölçüyor ve ölçümlerini paylaşıyor. Her ölçümle ekibin tahmini netleşiyor. Ama en değerli ölçümler kaynağa yakın olanlar, ve tam orası dozun en yüksek olduğu yer. Yani bilgi ile tehlike aynı yerde.

**Üçüncü adım, karar.** Her robot sürekli şu soruyu soruyor: aramaya devam mı edeyim, yoksa hâlâ çıkabiliyorken eve mi döneyim? Resimde mor robot bütçesinin çoğunu kullanmış, kapıya dönüyor; diğer ikisi aramaya devam ediyor.

Burada kritik bir nokta var: **eve dönmek de doz demek**, çünkü robot dönerken yine radyasyon alanından geçiyor. Bu yüzden robotun bütçe bittiğinde değil, dönüşe yetecek kadar kalmışken dönmesi gerekiyor.

---

## Slayt 4: Simüle edilen görev ve kurallar (~1 dk)

Bu slaytta simülasyonun kurallarını görüyorsunuz.

20'ye 20 metrelik, tek kapılı bir oda var; içindeki duvarlar radyasyonun bir kısmını engelliyor. İçeride 10 ile 100 terabekerel arasında güçlü bir Kobalt-60 kaynağı var; yeri ve gücü bilinmiyor. Ekipte 2 ile 6 arası robot bulunuyor ve tüm ölçümlerini paylaşıyorlar.

Fizik tarafında ters kare yasasını, yani mesafe yarıya inince dozun dört katına çıkmasını, ve duvarların radyasyonu zayıflatmasını modelliyorum. Dedektör sayımları rastgele, gerçekteki gibi. Ayrıca yaklaşık yüzde 30'luk, odanın içinde konuma göre değişen bir model hatası ekledim. Bu önemli bir tasarım kararıydı: hata olmadan problem fazla kolaydı, robotlar kaynağı uzaktan bulabiliyordu.

Her robot kendi toplam dozunu biliyor, tıpkı gerçek bir dozimetre gibi. Bütçe robot başına 0,1 gray. Bunu bir operasyon limiti olarak seçtim, donanım limiti olarak değil; gerçek elektronik genelde 100 gray civarında bozuluyor.

Başarıyı şöyle tanımlıyorum: ekip kaynağın gerçek yerine 1 metreden yakın bir konum ilan ederse görev başarılı. Herhangi bir robot bütçesini aşarsa ya da içeride mahsur kalırsa, o görev güvenlik ihlali sayılıyor. **Hedefim: görevlerin en fazla yüzde 5'inde ihlal.** Her sonuç 300 test görevi üzerinden ölçülüyor.

---

## Slayt 5: Literatürde ne var, ne eksik (~1 dk)

Robotlarla radyasyon araması aktif bir araştırma alanı, o yüzden neyin gerçekten yeni olduğunu dikkatle belirlemek istedim. Bu amaçla 428 makaleyi taradım.

Proctor ve arkadaşları pekiştirmeli öğrenmeyi bir parçacık filtresiyle birleştirmiş, ama tek robotla. Totten bunu robot ekiplerine genişletmiş, ama robotların kendi dozunu sınırlamamış. Huo ve arkadaşları 2026'da radyasyon dayanıklılığı farklı robotlar kullanmış, ama roller görev başlamadan sabitlenmiş ve dönüş için bir rezerv yok.

Güvenlik tarafında MAPPO-Lagrangian robot ekiplerine bir maliyet limiti ekliyor, ama sadece ortalama maliyeti sınırlıyor; benim ihtiyacım ise neredeyse hiçbir görevde hiçbir robotun aşmaması. En yakın yöntem 2026'daki SEA-MAPPO: robotun pilini tüketecek hareketleri engelliyor. Yani hareket engellemenin kendisini yeni olarak sunmuyorum.

**Benim farkım şu:** pil doğrudan ölçülebiliyor, ama radyasyonun tehlikesi bilinmiyor; ekibin belirsiz tahmininden hesaplanmak zorunda. Üstelik eve dönüşün de bir doz maliyeti var.

[Soru gelirse: en yakın yeni bulgu Dec-MARVEL (2026). Bütçe ve dönüş rezervi var, ama bütçesi sadece yol mesafesi; maliyeti aranan alanın tahminine bağlı değil.]

---

## Slayt 6: Şimdiye kadar ne kurdum (~1 dk 10 sn)

Bu slaytta sistemin dört parçasını görüyorsunuz.

Birincisi, hızlı bir çok robotlu radyasyon simülatörü. Çok sayıda görevi paralel çalıştırabiliyor.

İkincisi, ortak tahmin: 2000 olası kaynak konumunu ve gücünü aynı anda tutan bir parçacık filtresi. Aşağıdaki görsel gerçek bir test görevinden. Başta tahminler odanın her yerine dağılmış. Yaklaşık iki dakika sonra kaynağa doğru uzanan dar bir bant oluşturuyorlar, çünkü o ana kadarki ölçümler mesafeyi güçten henüz ayıramıyor. Sonunda da kaynağın üstünde sıkı bir kümede toplanıyorlar.

Üçüncüsü, robot politikaları: öğrenen MAPPO yöntemleri ve üç el yazımı strateji. Greedy en çok bilgi veren hareketi seçiyor, perimeter çevreden dolaşıyor, approach'ta ise herkes doğrudan kaynağa gidiyor.

Dördüncüsü, doz güvenlik katmanı; bir sonraki slaytta anlatacağım.

Bunların yanında 3D simülasyon için MuJoCo ve Gazebo, okulun süper bilgisayarı için iş betikleri ve 76 otomatik test var. Danışmanımın önerilerini de ekledim: her robot kendi dozunu takip ediyor, dönüş için rezerv tutuyor ve ölçümler her adımda paylaşılıyor.

---

## Slayt 7: Güvenlik katmanı (~1 dk 15 sn) [ANAHTAR SLAYT, yavaş anlat]

Bu, tezin çekirdek fikri.

Her hareketten önce her robot basit bir kuralı kontrol ediyor: **şimdiye kadar aldığım doz, artı bir sonraki adımın tahmini dozu, artı kapıya dönüşün tahmini dozu, 0,1 gray'i geçmemeli.**

Bu tahminler parçacık filtresinden geliyor. Ama kaynağın tam yerini bilmediğimiz için ortalama tahmini kullanmıyorum. Filtreden 32 olası kaynak senaryosu çekiyorum ve bunlar arasından kötü bir durumu, yani 97. yüzdeliği alıyorum. Basitçe: robot "kaynak sandığımdan daha güçlü veya daha yakın olabilir" diye pay bırakıyor.

Bir hareket kuralı bozuyorsa engelleniyor. Robot ise her zaman "geri çekil"i seçebiliyor: odadan çıkıyor ve takımın ödülünü paylaşmaya devam ediyor.

Sağdaki grafik gerçek bir test görevinden tek bir robotu gösteriyor. Siyah çizgi robotun gerçekte aldığı doz. Turuncu kesikli çizgi ise kuralın kontrol ettiği değer. Kesikli çizgi bütçeyi geçecek gibi olduğunda robot geri çekiliyor; çıkış dozu bir anda ekleniyor ve sonra dozu sabit kalıyor.

Dikkat çekici bir nokta var: bu robot 0,1 gray'in sadece 0,065'ini kullanarak çıktı. Yani kötümser tahmin temkinli davranıyor. Bu temkinin bir bedeli var; 9. slaytta ona döneceğim.

Son bir not: bu temkinli bir güvenlik mekanizması, matematiksel bir garanti değil. Robot çok sayıda karar veriyor, küçük riskler birikebilir. Bu yüzden gerçek ihlal oranını 300 görevde ölçüyorum.

---

## Slayt 8: Şimdiye kadarki sonuçlar (~1 dk 20 sn) [ANAHTAR SLAYT, yavaş anlat]

Sonuçları soldan sağa anlatayım. Önemli bir not: soldaki iki öğrenen yöntem, geri çekilme eylemini eklemeden önceki kurallarla ve tek eğitim çalıştırmasıyla elde edildi. Diğer üç sütun güncel kurallarla.

Standart öğrenme, yani MAPPO, kaynağı yüzde 85 bulabiliyor ama görevlerin yüzde 29'unda bir robot bütçesini aşıyor.

Doza bir fiyat koyan MAPPO-Lagrangian ihlali yüzde 6–7'ye indiriyor, ama başarı yüzde 10'a çöküyor. Robotlar kaynaktan yaklaşık 13 metre uzakta durmayı öğreniyor ve süre doluyor. Buna ürkeklik diyorum. Öğrenmeyi önceden eğitilmiş bir modelden başlatmak ve bir doz kalkanı eklemek başarıyı ancak yüzde 34'e çıkarabildi.

El yazımı greedy strateji MAPPO'ya benziyor: yüzde 85 başarı, yüzde 31 ihlal.

Şimdi ana sonuç: aynı greedy stratejiye güvenlik katmanını ve geri çekilmeyi eklediğimde **ihlal yüzde 31'den yüzde 4,3'e düşüyor**; bu 300 görevin 13'ü demek. **Başarı ise sadece yüzde 85'ten 84'e iniyor.**

Aynı kural kötümser tahmin yerine ortalama tahmini kullanırsa ihlal yüzde 14,7. Yani kötü durumu hesaba katmak gerçekten önemli.

Dürüst olmak gerekirse: yüzde 4,3'ün yüzde 95 güven aralığı 2,5 ile 7,3 arası. Yani nokta tahmin hedefin altında, ama aralık hâlâ yüzde 5'i geçiyor. Ayrıca bu sonuç el yazımı bir stratejiden geliyor.

---

## Slayt 9: Henüz çözülmemiş olanlar (~1 dk 10 sn)

Bu grafik tezimin şu anki en önemli açık problemi.

Her nokta güvenlik katmanının farklı bir ayarı: farklı yüzdelikler, güvenlik payları ve filtre ayarları. Toplam 13 ayar, her biri 300 görevle. Mavi nokta referansım: yüzde 84 başarı, yüzde 4,3 ihlal. Hiçbir ayar referansı her iki eksende birden geçemiyor. En temkinli ayar 300 görevde sadece 1 ihlal veriyor, ama başarı yüzde 65'e düşüyor. Yani daha güvenli olmak, başarıdan feragat etmek demek.

İkinci sorun, ortak tahminin aşırı emin olması. Filtre "yüzde 90 eminim" dediği bölgede kaynağı sadece yüzde 52–65 oranında içeriyor, ve görevlerin yüzde 12–19'unda ekip emin ama yanlış bir konum ilan ediyor. Muhtemel sebep şu: simülatördeki hatalar konuma göre birbirine bağlı, ama filtre her ölçümün hatasını bağımsız sayıyor, bu yüzden kendine fazla güveniyor. Filtreyi kalibre etmek bu güveni düzeltti, ama başarı–güvenlik dengesini iyileştirmedi.

Son olarak: yüzde 5'in altında olduğu henüz kanıtlanmadı, ve her şey şimdilik simülasyonda.

---

## Slayt 10: Plan (~1 dk)

Tezin geri kalanı için ana soru şu: **basit bir kural artı güvenlik katmanı zaten işe yarıyor. Öğrenen bir ekip, aynı güvenlik katmanının altında daha iyisini yapabilir mi?** Yani bir önceki grafikteki eğriyi yukarı ve sola itebilir mi?

Güvenlik olmadan öğrenen MAPPO ile greedy kural neredeyse aynı performansı gösteriyor, yüzde 85 başarı; bu yüzden bu adil bir karşılaştırma.

Birinci adım pilot. Bu pilot şu anda okulun süper bilgisayarında çalışıyor: üç yöntem, her biri üç tekrar. İkinci adım tam çalışma: on tekrar ve 3000'den fazla test görevi; bu, yüzde 4 civarındaki bir oranın gerçekten yüzde 5'in altında olduğunu göstermek için gereken büyüklük. Üçüncü adımda bütçeleri farklı robotlardan oluşan ekipleri inceleyeceğim: ekip riskli ölçümleri bütçesi fazla olan robota mı veriyor? Dördüncü adım filtrenin aşırı güvenini düzeltmek; literatür taramasında yaklaşık 20 makale bu problemi açık bir soru olarak belirtiyor. Beşinci adım gerçek robotlarda, simüle edilmiş radyasyonla veya zayıf bir test kaynağıyla bir deneme.

Kural tabanlı yaklaşım rekabetçi kalabilir de; bu da geçerli bir sonuç olur.

Kapanış olarak tek cümle: **güvenli arama, her robotun eve dönecek kadar doz bırakması demektir.** Teşekkür ederim, sorularınızı alabilirim.

---

## Olası sorular ve kısa cevaplar

| Soru | Cevap |
|---|---|
| Basit kural işe yarıyorsa neden öğrenme? | Kural sadece güvenlik–başarı eğrisi üzerinde kayıyor. Öğrenen bir ekip koordinasyonla eğriyi ileri itebilir mi, tezin asıl sorusu bu. Pilot şu an çalışıyor. |
| 0,1 Gy neden bu kadar düşük? | Doz kaynağın gücüyle doğru orantılı; önemli olan bütçe/aktivite oranı. 0,1 Gy ile 10–100 TBq, 100 Gy ile 10–100 PBq (endüstriyel ışınlayıcı veya reaktör enkazı) ile aynı dengeyi temsil ediyor. Ayrıca robot tekrar kullanılacağı için ömrünün bir payı. |
| Robot bütçe dolmadan bozulabilir mi? | Evet. Sensörler yüksek doz hızında anlık bozulabiliyor ve parçadan parçaya fark var. Modelim bunu basitleştiriyor; rastgele bütçe ve doz hızına bağlı sensör gürültüsünü deney olarak ekleyeceğim. |
| Neden 97. yüzdelik? | Ortalama tahmin yüzde 14,7 ihlal verdi; kötümser tahmin yüzde 4,3. Literatürün önerdiği alternatif CVaR (en kötü yüzde 3'ün ortalaması); bunu da deneyeceğim. |
| Bu bir garanti mi? | Hayır, temkinli bir mekanizma. Gerçek ihlal oranını ölçüyorum; tam çalışmada 3000+ görevle güven aralığını daraltacağım. |
| Gerçek robotta test? | Henüz yok. 3D simülasyonda (MuJoCo) aktarım testleri yaptım; gerçek robot planın son adımı. |
