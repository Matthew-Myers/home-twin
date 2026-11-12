# Material recipes that matched real stills (Poly Haven CC0, `rk.pbr`)

Fetch: `blender -b --python scripts/fetch_polyhaven.py -- tex:<id> ...` → `assets/polyhaven/<id>/`.
Apply: `rk.pbr(name, id, size=<real-world tile size from the asset page>, tint=, wash=(rgb, amount), normal=, rot3=)`.
`wash` pulls a texture toward a paint or stain colour while keeping its pattern. `tint` multiplies.

| surface | asset id | size m | settings | notes |
|---|---|---|---|---|
| painted concrete block | concrete_block_wall_03 | 1.81 | wash (paint rgb) 0.8, normal 0.45 | clear coursing survives the paint; _02 reads as plaster under paint |
| bare concrete block | concrete_block_wall_03 | 1.81 | wash mid-grey 0.55, normal 0.8 | _02 reads as rough stone at real size |
| knotty pine boards / panels | hinoki_planks | 1.89 | tint (1.1, 1.0, 0.9); rot3 for vertical boards | |
| dark stained boards | wood_plank_wall | 1.0 | rot3 for vertical boards | |
| butcher block / pine tops | wood_table | 1.0 | coat 0.1-0.2 | |
| rubber gym floor | rubber_tiles | 2.0 | tint ~0.45 grey | |
| painted basement floor | painted_concrete | 2.0 | wash (paint rgb) 0.55 | the asset is green; wash it |
| garage / bare concrete floor | garage_floor | 1.89 | | stained and worn |
| hardwood / parquet, veneers, plaster, tile | herringbone_parquet, wood_floor, white_oak_veneer, american_walnut_veneer, white_plaster_02, long_white_tiles, terrazzo_tiles | see page | | |

Procedural details worth reusing: perforated uprights (hole pattern from Generated coords), oriented boxes for
angled equipment, half discs cut at the wall plane. See roomkit (`obox`, `half_disc`, `hole_pattern_mat`).
