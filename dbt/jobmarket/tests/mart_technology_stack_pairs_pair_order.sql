select
    SkillKey1,
    SkillKey2
from {{ ref('mart_technology_stack_pairs') }}
where SkillKey1 >= SkillKey2
