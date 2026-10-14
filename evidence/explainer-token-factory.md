# Evidence: Verdict explanations checked number by number

Reproduce: `uv run --project backend --env-file .env python backend/scripts/check_explainer.py`, which writes this file and `explainer-token-factory.json`.

- **Measured:** 2026-10-14T16:12:57+00:00 on route `token-factory`, model `Gemma-4-31B-IT`, sample shop Glow Lab BKK.
- **Arena:** 3 SKUs decided in 117.5 s.
- **Explanations:** 6 (3 SKUs × Thai and English). 6 passed the number check on the first draft, 0 passed after a rewrite, and 0 fell back to the numbers-only template.
- **What the check proves:** every number in a shown explanation is a figure from the engine's fact sheet (rounding allowed). It does not prove that each number is attached to the right label, so the explanation is shown next to the engine's own table of figures.

| SKU | Verdict | Language | Source | Drafts rejected | Seconds |
|---|---|---|---|---|---|
| NT-200 | approve | th | model | none | 11.8 |
| NT-200 | approve | en | model | none | 5.3 |
| VC-30 | escalate | th | model | none | 7.3 |
| VC-30 | escalate | en | model | none | 3.7 |
| SM-10 | skip | th | model | none | 5.1 |
| SM-10 | skip | en | model | none | 3.3 |

## The explanations, as shown

**NT-200 (th, model)**

> แนะนำให้ Approve เพื่อเข้าร่วม Campaign ตามที่ได้รับเชิญครับ เพราะจะช่วยให้กำไรในกรณีที่แย่ที่สุดสูงถึง 45,421.56 บาท ซึ่งดีกว่าการไม่เข้าร่วม แผนนี้ผ่านการทดสอบกับ 183 Promo Plans และรับมือกับ Counter-move ที่ยากที่สุดคือ Undercutter ที่ลดราคาเหลือ 271.05 บาท โดยที่ร้านยังคงมี Margin Floor ต่ำสุดที่ 10.0% และได้กำไรต่อชิ้น 42.3% ของราคาขายครับ

**NT-200 (en, model)**

> Approve the Promo Plan to join the Campaign. This is better because your worst-case profit is 45,421.56 Thai Baht, compared to 17,695.71 Thai Baht if you do not join. The plan was tested against an Undercutter Counter-move with a rival price of 271.05 Thai Baht.

**VC-30 (th, model)**

> คุณควร Escalate เพื่อตัดสินใจเลือก Promo Plan เอง เพราะไม่มีแผนไหนผ่านทุกเกณฑ์ โดยเฉพาะการเข้าร่วม Campaign ที่ทำให้กำไรต่อหน่วยเหลือ 8.4% ซึ่งต่ำกว่า Margin Floor ที่ 10.0% แผนนี้ถูกทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ซึ่งคู่แข่งตั้งราคา 282.00 บาท

**VC-30 (en, model)**

> You must Escalate this decision because no Promo Plan meets your 10.0% Margin Floor. Joining the Campaign results in a worst-case margin per unit of 8.4%. This plan was tested against an Undercutter Counter-move with a rival price of 282.00 Thai Baht.

**SM-10 (th, model)**

> แนะนำให้ Skip การเข้าร่วม Campaign นี้สำหรับสินค้าตัวนี้ครับ เพราะจะทำให้ได้กำไรต่อชิ้นเพียง 4.5% ซึ่งต่ำกว่า Margin Floor ที่คุณตั้งไว้ 10.0% และได้กำไรน้อยกว่าการไม่เข้าร่วมด้วย โดยแผนนี้ผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Price matcher ที่คู่แข่งลดราคาเหลือ 229.20 บาท

**SM-10 (en, model)**

> You should Skip this Campaign for your Hyaluronic Sheet Mask x10. Joining as invited would lead to a worst-case margin per unit of 4.5%, which is below your 10.0% Margin Floor. This plan was tested against a Price matcher Counter-move where a rival price was 229.20 Thai Baht.

## Read by hand (added after the run, 14 Oct 2026)

Every number above is an engine figure. Read against the fact sheets, the labels are right in 5 of the 6
explanations. The exception: the Thai NT-200 text says the plan was "tested against 183 Promo Plans", but the
engine searched 183 Promo Plans and tested the leader against the Counter-moves. Rerunning the script replaces
the explanations, so this review applies to this run only.
