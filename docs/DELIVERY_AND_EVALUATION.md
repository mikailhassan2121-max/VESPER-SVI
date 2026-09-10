# Delivery and evaluation contracts

Telegram behavior follows the [official Bot API](https://core.telegram.org/bots/api) and [update-offset guidance](https://core.telegram.org/bots/faq). Polling advances a persisted offset and restricts replies to the configured chat. HTTP 429 receives a bounded retry delay; an ambiguous transport failure becomes UNKNOWN. Telegram does not provide a transaction shared with SQLite, so this implementation does not promise exactly-once delivery. A process interruption during sending requires investigation rather than blind retry.

Calibration uses chronological out-of-fold predictions and logistic sigmoid fitting, following the separation principle in the [scikit-learn calibration documentation](https://scikit-learn.org/stable/modules/calibration.html). Calibration-training fit is not acceptance evidence. Locked test and future observations are needed to assess reliability. Fewer than 50 observations of either class leaves that probability uncalibrated.

The locked-test registry refuses overlapping date intervals even if the dataset changes. It cannot prevent an operator from copying data to another registry or manually deleting files; preserve the registry as part of the research audit trail. No automated production-promotion command is provided yet.
