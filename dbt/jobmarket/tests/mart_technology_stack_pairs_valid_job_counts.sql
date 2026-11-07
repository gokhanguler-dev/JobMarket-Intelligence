select
    SkillKey1,
    SkillKey2,
    BothJobs,
    Skill1Jobs,
    Skill2Jobs,
    TotalJobs
from {{ ref('mart_technology_stack_pairs') }}
where BothJobs > Skill1Jobs
   or BothJobs > Skill2Jobs
   or BothJobs > TotalJobs
