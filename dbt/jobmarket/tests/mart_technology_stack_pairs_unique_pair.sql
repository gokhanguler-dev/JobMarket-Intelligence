select
    SkillKey1,
    SkillKey2,
    count(*) as PairRowCount
from {{ ref('mart_technology_stack_pairs') }}
group by
    SkillKey1,
    SkillKey2
having count(*) > 1
