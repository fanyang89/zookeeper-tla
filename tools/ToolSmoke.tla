--------------------------- MODULE ToolSmoke ---------------------------
EXTENDS Naturals

VARIABLE
    (* @type: Int; *)
    x

Init == x = 0
Next == x' = IF x < 2 THEN x + 1 ELSE x
TypeOK == x \in 0..2

=============================================================================
