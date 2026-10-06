# Evaluation Report

## Overall Metrics
- **Precision:** 0.6667
- **Recall:** 0.7692
- **F1 Score:** 0.7143

## Misses (False Negatives)
| Text | Missed Phrase |
|---|---|
| This code is completely wrong and you need to fix this. | this is wrong |
| We should table the motion until the next meeting. | tabling a motion |
| I will try to get it done. | i'll try |

## False Positives
| Text | False Positive |
|---|---|
| Please submit the report by 5 PM EST on Friday. | by 5 pm |
| We should table the motion until the next meeting. | table the motion |
| I will try to get it done. | i will try |
| Yeah right, like that's going to work. | that's going to work. |
| We need to bite the bullet. | we need to |