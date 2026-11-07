select
    SkillKey1,
    SkillKey2,
    SupportPct,
    Confidence1To2Pct,
    Confidence2To1Pct
from {{ ref('mart_technology_stack_pairs') }}
where SupportPct not between 0 and 100
   or Confidence1To2Pct not between 0 and 100
   or Confidence2To1Pct not between 0 and 100
