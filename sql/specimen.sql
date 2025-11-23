select * from testing_specimen ts
left join tracking_children tc on tc.id_patient_child=ts.id_patient
left join patient mp on mp.id = tc.id_patient_mother
where ts.date_blood_taken>"2025-07-01"

