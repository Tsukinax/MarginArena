# Evidence: Gemma's explanations of the recorded run's 12 Verdicts

Reproduce: `uv run --project backend --env-file .env python backend/scripts/record_explanations.py --expect-route token-factory` (sample data only).

- **Written:** 2026-10-17T11:17:32+00:00 on token-factory, for the Verdicts of `token-factory-sample-12sku.sse` (recorded 2026-10-14T19:51:51+00:00).
- **Asked:** 32 explanations (12 Verdicts × English and Thai), through `/api/explain` with `live`.
- **Passed the number check on the first draft:** 32; **after one rewrite:** 0; **numbers-only template:** 0; **written by a model other than Gemma-4-31B-IT:** 0.
- **Served by the app:** the 24 that Gemma-4-31B-IT wrote and that passed the check, each only for the exact Verdict it explains (`api.result_digest`), labelled as recorded. Any other request asks the model live.
- **The check proves numbers, not labels:** a right number can still sit next to the wrong words, so a person reads every text. Asked again after that review: 8; no longer served: none. Every answer is below, in the order asked.

| SKU | Verdict | Language | Source | Rejected drafts | Model | Seconds |
|---|---|---|---|---|---|---|
| HB-30 | approve | en | model | 0 | Gemma-4-31B-IT | 6.5 |
| HB-30 | approve | th | model | 0 | Gemma-4-31B-IT | 7.7 |
| NT-200 | approve | en | model | 0 | Gemma-4-31B-IT | 19.7 |
| NT-200 | approve | th | model | 0 | Gemma-4-31B-IT | 17.1 |
| SS-50 | revise | en | model | 0 | Gemma-4-31B-IT | 25.2 |
| SS-50 | revise | th | model | 0 | Gemma-4-31B-IT | 21.1 |
| CN-50 | approve | en | model | 0 | Gemma-4-31B-IT | 7.3 |
| CN-50 | approve | th | model | 0 | Gemma-4-31B-IT | 32.4 |
| VC-30 | escalate | en | model | 0 | Gemma-4-31B-IT | 23.9 |
| VC-30 | escalate | th | model | 0 | Gemma-4-31B-IT | 17.3 |
| AC-150 | approve | en | model | 0 | Gemma-4-31B-IT | 8.8 |
| AC-150 | approve | th | model | 0 | Gemma-4-31B-IT | 50.7 |
| RN-30 | skip | en | model | 0 | Gemma-4-31B-IT | 21.9 |
| RN-30 | skip | th | model | 0 | Gemma-4-31B-IT | 25.3 |
| CG-80 | approve | en | model | 0 | Gemma-4-31B-IT | 11.7 |
| CG-80 | approve | th | model | 0 | Gemma-4-31B-IT | 13.4 |
| LM-15 | approve | en | model | 0 | Gemma-4-31B-IT | 13.4 |
| LM-15 | approve | th | model | 0 | Gemma-4-31B-IT | 15.0 |
| SM-10 | skip | en | model | 0 | Gemma-4-31B-IT | 9.7 |
| SM-10 | skip | th | model | 0 | Gemma-4-31B-IT | 6.1 |
| CM-100 | approve | en | model | 0 | Gemma-4-31B-IT | 7.0 |
| CM-100 | approve | th | model | 0 | Gemma-4-31B-IT | 6.1 |
| TK-4 | approve | en | model | 0 | Gemma-4-31B-IT | 8.4 |
| TK-4 | approve | th | model | 0 | Gemma-4-31B-IT | 40.9 |
| SS-50 | revise | th | model | 0 | Gemma-4-31B-IT | 8.7 |
| CN-50 | approve | th | model | 0 | Gemma-4-31B-IT | 13.5 |
| AC-150 | approve | th | model | 0 | Gemma-4-31B-IT | 12.3 |
| RN-30 | skip | en | model | 0 | Gemma-4-31B-IT | 7.2 |
| LM-15 | approve | th | model | 0 | Gemma-4-31B-IT | 27.5 |
| SS-50 | revise | th | model | 0 | Gemma-4-31B-IT | 77.3 |
| CN-50 | approve | th | model | 0 | Gemma-4-31B-IT | 45.5 |
| AC-150 | approve | th | model | 0 | Gemma-4-31B-IT | 12.1 |

## The texts

**HB-30 (approve), en, model:** Approve the Promo Plan and join the Campaign as invited. This is because your worst-case Campaign profit is 41,139.00 Thai Baht, which is higher than the 16,366.77 Thai Baht profit if you do not join. The plan was tested against an Undercutter Counter-move with a rival price of 414.10 Thai Baht.

**HB-30 (approve), th, model:** แนะนำให้ Approve เข้าร่วม Campaign ตามที่ได้รับเชิญได้เลย เพราะจะช่วยสร้างกำไรในกรณีแย่ที่สุดได้ถึง 41,139.00 บาท ซึ่งสูงกว่าการไม่เข้าร่วม โดยแผนนี้มี Margin Floor อยู่ที่ 10.0% และผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ที่ลดราคาเหลือ 414.10 บาท

**NT-200 (approve), en, model:** Approve and join the Campaign as invited. This plan is better because your worst-case Campaign profit is 43,599.09 Thai Baht, compared to 16,965.99 Thai Baht if you do not join. It was tested against an Undercutter Counter-move with a rival price of 260.28 Thai Baht. Your worst-case margin per unit remains 42.3 percent, which is above your 10.0 percent Margin Floor.

**NT-200 (approve), th, model:** แนะนำให้ Approve เข้าร่วม Campaign ตามที่ได้รับเชิญครับ เพราะจะช่วยสร้างกำไรในกรณีเลวร้ายที่สุดได้ถึง 43,599.09 บาท ซึ่งสูงกว่าการไม่เข้าร่วม โดยแผนนี้ผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ซึ่งลดราคาเหลือ 260.28 บาท แต่เรายังคงรักษา Margin per unit ไว้ได้ที่ 42.3% ซึ่งสูงกว่า Margin Floor ที่ตั้งไว้ 10.0% ครับ

**SS-50 (revise), en, model:** Revise your strategy and join the Campaign using the Promo Plan. This ensures a worst-case Campaign profit of 67,897.70 Thai Baht while staying above your 10.0% Margin Floor. The plan was tested against an Undercutter Counter-move with a rival price of 234.00 Thai Baht.

**SS-50 (revise), th, model:** แนะนำให้ Revise โดยเข้าร่วม Campaign ด้วย Promo Plan ของ MarginArena แทนแผนที่ถูกเชิญมา เพื่อให้ได้กำไร Campaign ในกรณีแย่ที่สุด 67,897.70 บาท ซึ่งสูงกว่าการไม่เข้าร่วม แผนนี้ถูกทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ที่ตั้งราคาคู่แข่ง 234.00 บาท โดยยังคงรักษา Margin Floor ไว้ได้ที่ 30.8% ของราคาขาย

**CN-50 (approve), en, model:** Approve the Promo Plan and join the Campaign as invited. This keeps your worst-case margin per unit at 15.7%, which stays above your 10.0% Margin Floor. The plan was tested against an Undercutter Counter-move with a rival price of 465.50 Thai Baht.

**CN-50 (approve), th, model:** แนะนำให้ Approve เข้าร่วม Campaign ตามที่ได้รับเชิญ เพราะจะช่วยสร้างกำไรคาดการณ์ได้ 14,919.76 บาท ซึ่งสูงกว่าการไม่เข้าร่วม แผนนี้ผ่านการทดสอบกับ 73 Promo Plans เพื่อให้มั่นใจว่ากำไรต่อชิ้นจะอยู่ที่ 15.7% ซึ่งสูงกว่า Margin Floor ที่คุณตั้งไว้ 10.0% โดยแผนนี้ทนทานต่อ Counter-move ที่ยากที่สุดคือ Undercutter ที่คู่แข่งลดราคาลงเหลือ 465.50 บาท

**VC-30 (escalate), en, model:** Please Escalate this decision because no Promo Plan meets your 10.0% Margin Floor. Joining the Campaign may result in a worst-case margin per unit of 8.4%. This plan was tested against an Undercutter Counter-move with a rival price of 370.20 Thai Baht.

**VC-30 (escalate), th, model:** คุณต้องตัดสินใจเองว่าจะ Approve หรือ Revise เพราะไม่มี Promo Plan ไหนผ่านทุกเกณฑ์ โดยการเข้าร่วม Campaign จะทำให้กำไรต่อชิ้นต่ำสุดอยู่ที่ 8.4% ซึ่งน้อยกว่า Margin Floor ที่คุณตั้งไว้ 10.0% แผนนี้ถูกทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ซึ่งคู่แข่งลดราคาเหลือ 370.20 บาท แต่คุณจะยังคงมีกำไร Campaign ในกรณีแย่ที่สุดอยู่ที่ 7,369.32 บาท

**AC-150 (approve), en, model:** Approve the Promo Plan and join the Campaign as invited. This ensures a worst-case Campaign profit of 53,782.92 Thai Baht, which is higher than the 20,846.25 Thai Baht profit from not joining. The plan was tested against an Undercutter Counter-move with a rival price of 186.05 Thai Baht.

**AC-150 (approve), th, model:** แนะนำให้ Approve เพื่อเข้าร่วม Campaign ตามที่ได้รับเชิญครับ เพราะจะช่วยสร้างกำไรในกรณีที่แย่ที่สุดได้ 53,782.92 บาท ซึ่งมากกว่าการไม่เข้าร่วม โดยแผนนี้ผ่านการทดสอบกับ 183 Promo Plans และทนทานต่อ Counter-move ที่ยากที่สุดคือ Undercutter ซึ่งคู่แข่งลดราคาเหลือ 186.05 บาท แต่คุณจะยังคงมี Margin Floor อยู่ที่ 42.5% ต่อชิ้นครับ

**RN-30 (skip), en, model:** You should Skip this Campaign because the 5.3% margin per unit is below your 10.0% Margin Floor. Following this Verdict protects 861.03 Thai Baht of your margin. This Promo Plan was tested against 183 Promo Plans and the hardest Counter-move was a price matcher with a rival price of 452.50 Thai Baht.

**RN-30 (skip), th, model:** แนะนำให้ Skip หรือไม่เข้าร่วม Campaign นี้กับสินค้าตัวนี้ครับ เพราะจะทำให้กำไรต่อชิ้นลดลงเหลือ 5.3% ซึ่งต่ำกว่า Margin Floor ที่ 10.0% ที่คุณตั้งไว้ การไม่เข้าร่วมจะช่วยรักษา Margin ได้ 861.03 บาท โดยแผนนี้ผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Price matcher ซึ่งคู่แข่งลดราคาเหลือ 452.50 บาท และตรวจสอบผ่าน 183 Promo Plans แล้วครับ

**CG-80 (approve), en, model:** Approve the Promo Plan and join the Campaign as invited. This is because your worst-case Campaign profit reaches 25,472.70 Thai Baht and your worst-case margin per unit is 43.2 percent, which stays above your 10.0 percent Margin Floor. The plan was tested against an Undercutter Counter-move with a rival price of 174.00 Thai Baht.

**CG-80 (approve), th, model:** แนะนำให้ Approve เพื่อเข้าร่วม Campaign ตามที่ได้รับเชิญครับ เพราะจะช่วยให้ได้กำไรในกรณีที่แย่ที่สุด 25,472.70 บาท ซึ่งสูงกว่าการไม่เข้าร่วมที่ได้เพียง 9,826.45 บาท โดยมี Margin Floor อยู่ที่ 10.0% และแผนนี้ผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ที่ลดราคาเหลือ 174.00 บาท โดยการใช้ Promo Plan นี้ยังคงรักษาผลกำไรในกรณีเลวร้ายที่สุดไว้ได้

**LM-15 (approve), en, model:** Approve the Promo Plan and join the Campaign as invited. This is because your worst-case margin per unit is 42.7%, which is above your 10.0% Margin Floor. The plan was tested against an Undercutter Counter-move with a rival price of 100.00 Thai Baht.

**LM-15 (approve), th, model:** แนะนำให้ Approve เข้าร่วม Campaign ตามที่ได้รับเชิญ เพราะจะช่วยให้กำไรในกรณีที่แย่ที่สุดสูงถึง 20,213.73 บาท ซึ่งดีกว่าการไม่เข้าร่วม แผนนี้ถูกทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ที่ลดราคาเหลือ 100.00 บาท โดยยังคงรักษา Margin Floor ไว้ได้ที่ 42.7% ของราคาขาย ซึ่งสูงกว่าเกณฑ์ขั้นต่ำที่คุณตั้งไว้

**SM-10 (skip), en, model:** You should Skip the Campaign for this product. Joining leads to a 4.5% margin per unit, which is below your 10.0% Margin Floor. The plan was tested against an Undercutter Counter-move with a rival price of 231.22 Baht.

**SM-10 (skip), th, model:** แนะนำให้ Skip หรือไม่เข้าร่วม Campaign ด้วยสินค้าชิ้นนี้ เพราะจะทำให้กำไรต่อหน่วยเหลือเพียง 4.5% ซึ่งต่ำกว่า Margin Floor ที่คุณตั้งไว้ 10.0% การไม่เข้าร่วมจะช่วยรักษา Margin ได้ 787.47 บาท และให้กำไรในกรณีแย่ที่สุดสูงถึง 3,092.99 บาท โดยแผนนี้ผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ซึ่งคู่แข่งลดราคาลงเหลือ 231.22 บาท

**CM-100 (approve), en, model:** Approve the Promo Plan and join the Campaign as invited. This is because your worst-case Campaign profit is 24,133.50 Thai Baht, which is better than the 9,507.97 Thai Baht profit from not joining. The plan was tested against an Undercutter Counter-move with a rival price of 228.00 Thai Baht. Your worst-case margin per unit remains 39.4 percent, which is above your 10.0 percent Margin Floor.

**CM-100 (approve), th, model:** แนะนำให้ Approve เข้าร่วม Campaign ตามที่ได้รับคำเชิญครับ เพราะจะช่วยให้ได้กำไรในกรณีแย่ที่สุดถึง 24,133.50 บาท ซึ่งดีกว่าการไม่เข้าร่วมที่ได้เพียง 9,507.97 บาท โดยมี Margin Floor อยู่ที่ 10.0% และแผนนี้ผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ที่คู่แข่งลดราคาเหลือ 228.00 บาท

**TK-4 (approve), en, model:** Approve the Promo Plan and join the Campaign as invited. This is because your worst-case margin per unit is 17.1%, which stays above your 10.0% Margin Floor. This plan was tested against a Price matcher Counter-move with a rival price of 334.25 Thai Baht.

**TK-4 (approve), th, model:** แนะนำให้ Approve เข้าร่วม Campaign ตามคำเชิญ เพราะจะทำให้ได้กำไรในกรณีแย่ที่สุด 8,902.95 บาท ซึ่งมากกว่าการไม่เข้าร่วมที่ได้เพียง 5,085.63 บาท โดยกำไรต่อชิ้นในกรณีแย่ที่สุดจะอยู่ที่ 17.1% ซึ่งยังสูงกว่า Margin Floor ที่ 10.0% แผนนี้ผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Price matcher ซึ่งคู่แข่งลดราคาเหลือ 334.25 บาท

**SS-50 (revise), th, model:** แนะนำให้ Revise โดยเข้าร่วม Campaign ด้วย Promo Plan ของ MarginArena แทนแผนที่ได้รับเชิญ เพื่อให้ได้กำไรในกรณีเลวร้ายที่สุด 67,897.70 บาท ซึ่งสูงกว่าการไม่เข้าร่วม แผนนี้ผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ที่ลดราคาเหลือ 234.00 บาท โดยยังรักษา Margin Floor ไว้ได้ที่ 30.8% ของราคาขาย

**CN-50 (approve), th, model:** แนะนำให้ Approve เพื่อเข้าร่วม Campaign ตามที่ได้รับเชิญ เพราะจะทำกำไรสูงสุดในกรณีที่แย่ที่สุดได้ 11,347.98 บาท ซึ่งมากกว่าการไม่เข้าร่วม โดยแผนนี้มี Margin Floor อยู่ที่ 10.0% และมีกำไรต่อชิ้นต่ำสุด 15.7% ของราคาขาย แผนนี้ผ่านการทดสอบกับ 73 Promo Plans และทนทานต่อ Counter-move ที่ยากที่สุดคือ Undercutter ที่ลดราคาเหลือ 465.50 บาท

**AC-150 (approve), th, model:** แนะนำให้ Approve เข้าร่วม Campaign ตามที่ได้รับเชิญครับ เพราะจะช่วยให้ได้กำไรในกรณีที่แย่ที่สุด 53,782.92 บาท ซึ่งสูงกว่าการไม่เข้าร่วมที่ได้เพียง 20,846.25 บาท และยังมี Margin per unit ต่ำสุดที่ 42.5% ซึ่งสูงกว่า Margin Floor ที่ 10.0% ของคุณ แผนนี้ผ่านการทดสอบกับ 183 Promo Plans โดยรับมือกับ Counter-move ที่ยากที่สุดคือ Undercutter ที่ลดราคาเหลือ 186.05 บาท ได้อย่างมีประสิทธิภาพ

**RN-30 (skip), en, model:** You should Skip this Campaign. Joining leads to a worst-case margin per unit of 5.3%, which is below your 10.0% Margin Floor. This plan was tested against a Price matcher Counter-move with a rival price of 452.50 Thai Baht.

**LM-15 (approve), th, model:** แนะนำให้ Approve เข้าร่วม Campaign ตามที่ได้รับเชิญครับ เพราะจะช่วยให้ได้กำไรในกรณีเลวร้ายที่สุด 20,213.73 บาท ซึ่งสูงกว่าการไม่เข้าร่วมที่ได้เพียง 7,767.68 บาท โดยแผนนี้มี Margin Floor อยู่ที่ 10.0% และผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ที่ลดราคาเหลือ 100.00 บาท

**SS-50 (revise), th, model:** แนะนำให้ Revise โดยเข้าร่วม Campaign ด้วย Promo Plan ของ MarginArena แทนข้อเสนอที่ได้รับ เพื่อให้ได้กำไรในกรณีเลวร้ายที่สุด 67,897.70 บาท ซึ่งสูงกว่าการไม่เข้าร่วมที่มีกำไรเพียง 22,206.57 บาท โดยแผนนี้ยังรักษา Margin Floor ของคุณที่ 10.0% ได้อย่างปลอดภัย แผนนี้ผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ซึ่งลดราคาคู่แข่งเหลือ 234.00 บาท

**CN-50 (approve), th, model:** แนะนำให้ Approve เพื่อเข้าร่วม Campaign ตามที่ได้รับคำเชิญครับ เพราะจะช่วยสร้างกำไรในกรณีที่แย่ที่สุดได้ 11,347.98 บาท ซึ่งดีกว่าการไม่เข้าร่วมที่ได้เพียง 6,177.89 บาท โดยแผนนี้ผ่านการทดสอบกับ 7 Counter-moves ซึ่งตัวที่รับมือยากที่สุดคือ Undercutter ที่ลดราคาเหลือ 465.50 บาท แต่คุณจะยังคงมี Margin Floor อยู่ที่ 10.0% และได้กำไรต่อชิ้น 15.7% ของราคาขายครับ

**AC-150 (approve), th, model:** แนะนำให้ Approve เพื่อเข้าร่วม Campaign ตามที่ได้รับเชิญ เพราะจะช่วยให้ได้กำไรสูงสุดในกรณีเลวร้ายที่สุด 53,782.92 บาท ซึ่งมากกว่าการไม่เข้าร่วมที่ได้เพียง 20,846.25 บาท โดยระบบได้ทดสอบ Promo Plan นี้กับ 7 Counter-moves และผ่านการทดสอบกับ Counter-move ที่ยากที่สุดคือ Undercutter ซึ่งคู่แข่งลดราคาเหลือ 186.05 บาท โดยที่คุณยังรักษาระดับ Margin Floor ได้ที่ 10.0%

## Hand review (Claude, 17 Oct 2026, about 18:30-18:50 ICT)

Every text was read against its Verdict's figures, because the number check proves numbers, not labels.

- **First pass (24 asked):** 19 clean. 5 put a right number on the wrong label: SS-50 (th), AC-150 (th) and LM-15
  (th) called the product's worst-case margin per unit (30.8%, 42.5%, 42.7%) the "Margin Floor", which is the
  Seller's 10.0%; CN-50 (th), AC-150 (th) and RN-30 (en) said the plan was "tested against" 73 or 183 Promo Plans,
  which is how many plans the engine compared.
- **Second pass (those 5 asked again, same facts):** RN-30 (en) and LM-15 (th) clean; SS-50, CN-50 and AC-150 (th)
  repeated the same mistakes.
- **Fix, then a third pass:** the fact sheet now gives "The engine compared N Promo Plans" its own sentence, apart
  from "tested against N Counter-moves", and the prompt says only the Seller's minimum may be called the Margin
  Floor (`backend/src/marginarena/explainer.py`; test in `backend/tests/api/test_explain_api.py`). Asked again, all
  three were clean.
- **Served:** the 24 latest texts, one per Verdict and language, all written by Gemma-4-31B-IT, all read clean. The 8
  superseded answers stay in the table and texts above. 21 of the 24 served texts were written with the earlier fact
  sheet and prompt.
- No served text presents the Rivals' Counter-moves as risk only AI found.
