# Fair Bench synthetic demo dataset

This manifest contains 36 fully synthetic identities balanced across age,
gender, and ethnicity labels. The backend seeds the same records automatically
on first start, so the complete dashboard is immediately usable.

该清单包含 36 个完全虚构的演示身份，覆盖年龄、性别与族裔分组。后端首次启动时会
自动写入同一套数据和四组算法评测记录，可直接体验看板、失败样本与报告流程。

The records and 36 generated SVG portrait fixtures in `images/` are for
software demonstrations only. They are not biometric data, do not identify real
people, and must not be used to validate production model performance. Run
`python3 generate_demo_images.py` to regenerate the fixtures deterministically.

这些记录及 `images/` 中的 36 个合成 SVG 肖像仅用于软件演示，不属于真实生物特征
数据，不对应任何自然人，也不能用于证明生产算法的真实性能。执行
`python3 generate_demo_images.py` 可确定性地重新生成全部图片。
