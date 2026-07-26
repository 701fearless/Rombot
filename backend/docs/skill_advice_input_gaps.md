# Skill advice input gaps

The saved `SceneSnapshot` already provides furniture IDs, source, semantics,
dimensions, position, rotation, scale, placement surface, room polygon and walls.
The customized export is written under `backend/user/<user-id>/floorplans/` and
retains the original export fields.

The current floorplan data does not reliably provide:

- structured door/window position, size, opening direction and clearance zone;
- measured-versus-estimated provenance for every newly added furniture size;
- furniture safety evidence such as anchoring, edge shape, load rating, cords,
  glass, stability, material claims and verified certifications;
- room/zone ownership for every object in a multi-room floorplan;
- compass orientation, entrance facing and reliable construction year for the
  feng-shui timing layer;
- child age/mobility/behaviour or pet species/behaviour unless the user selects
  and enters them in the editor;
- household constraints such as accessibility needs, allergies, rental limits,
  budget and willingness to drill or install fixtures.

The API reports applicable gaps in `missingFields`. Unknown values are not
invented and recommendations that depend on them must remain conditional.
