# 데이터 구성과 재생성

GitHub에는 아래 작은 실행용 데이터 3개를 포함합니다. 원본 다운로드와 중간 파일은 프로젝트에 포함하지 않으며, 기본 실행과 테스트에는 필요하지 않습니다.

| 파일 | 행 수 | 출처와 상태 |
|---|---:|---|
| `processed/patients_model.csv` | 236 | NHANES 관측 자료를 가공한 당뇨 진단 + 암 병력 표본. `record_source=nhanes_observed`이며 합성 환자 자료가 아닙니다. |
| `processed/foods_model.csv` | 77 | FoodData Central Survey (FNDDS 2021–2023, 사용한 배포본 이름의 날짜: 2024-10-31)에서 추린 음식의 영양소·제공량 자료. |
| `processed/food_annotation.csv` | 77 | 음식의 질감·맛 등을 붙인 프로젝트 초안. 전부 `annotator=claude_draft`, `reviewed=0`이며 FNDDS 관측값이나 검토 완료 자료가 아닙니다. |

환자 자료의 증상·치료 상태는 관측되지 않아 비어 있습니다. `personas/`는 주로 NHANES 관측값에 가상 증상을 더한 시나리오이며, 완전 합성 사례는 별도로 표시합니다. 데이터 해석과 한계는 [프로젝트 README](../README.md), annotation 값과 검토 상태는 [food_annotation.csv](processed/food_annotation.csv)를 참고하세요.

## 선택: 원본을 별도로 준비해 재생성

재생성이 필요할 때만 원본을 별도로 확보한 뒤 아래 위치에 준비합니다. 경로는 프로젝트 루트 기준이며, 현재 이 원본 파일들은 들어 있지 않습니다.

| 자료 | 준비할 위치 |
|---|---|
| FNDDS 2021–2023 Survey CSV 배포본 | `data/raw/fndds/`에 CSV 파일을 직접 배치 |
| 정리된 NHANES 환자 CSV | `data/raw/nhanes_csv/patients_final.csv` |
| 코호트 감사용 NHANES 원본 XPT | 예: `raw_data/`; 감사 스크립트에 폴더를 인자로 전달 |

음식 빌드에는 `food.csv`, `survey_fndds_food.csv`, `wweia_food_category.csv`, `food_nutrient.csv`, `food_portion.csv`가 필요하며, 감사에는 `nutrient.csv`, `food_attribute.csv`도 사용합니다. Foundation CSV/JSON과 Survey JSON은 이 절차에 사용하지 않습니다.

PowerShell에서 입력 폴더를 만든 뒤 확보한 자료를 위 위치에 넣습니다.

```powershell
New-Item -ItemType Directory -Force -Path 'data/raw/fndds', 'data/raw/nhanes_csv' | Out-Null
```

입력 자료를 준비한 뒤 프로젝트 루트에서 실행합니다. 빌드 명령은 `data/processed/`의 해당 가공 CSV를 다시 씁니다.

```powershell
python scripts/build_patients_model.py
python scripts/build_foods_model.py
python scripts/audit_uploads.py
python -m unittest discover -s tests -v
```

음식 빌드는 포함된 `food_annotation.csv`의 음식 ID를 사용하며, 77행 후보 파일 외에 전체 음식의 `data/processed/foods_all_nutrients.csv`도 생성합니다. 전체 음식 파일은 기본 실행에 필요하지 않아 저장소에서 제외합니다.

NHANES XPT를 `raw_data/`에 별도로 준비했다면 코호트 감사도 실행할 수 있습니다. 대상 파일은 `DEMO_L`, `DIQ_L`, `MCQ_L`, `BMX_L`, `GHB_L`, `DR1TOT_L`, `DR1IFF_L`, `DRXFCD_L`의 `.xpt`이며, `DR1IFF_L` 음식 코드 연결 검사에는 `data/raw/fndds/survey_fndds_food.csv`도 필요합니다.

```powershell
python scripts/cohort_audit_xpt.py raw_data
```

## 환자 입력 CSV 준비

환자 빌드에는 이미 정리된 `data/raw/nhanes_csv/patients_final.csv`가 필요합니다. 원본 NHANES XPT를 병합해 이 CSV를 생성하는 전처리 코드는 이 저장소에 포함되어 있지 않으므로 입력 파일을 별도로 준비해야 합니다. 필요한 열과 가공 방식은 [build_patients_model.py](../scripts/build_patients_model.py)를 참고하세요. 원본·중간 파일은 `.gitignore`로 제외됩니다.
