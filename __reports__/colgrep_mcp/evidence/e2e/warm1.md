[09/12/26 00:28:33] INFO     colgrep-mcp 0.1.0 starting:          __main__.py:31
                             binary=colgrep                                     
                             root=/Users/me/projects               
                             /_colgrep_e2e_corpus/click                         
                             timeout_s=600.0                                    
[09/12/26 00:28:38] INFO     Tool 'index_clear' failed: 'Error     server.py:444
                             executing tool index_clear:                        
                             [CONFIRMATION_REQUIRED] Refusing to                
                             delete the index for                               
                             /Users/me/projects/p141              
                             rep_e2e_corpus/click without                       
                             confirmation. Next: Call again with                
                             `confirm=true`.'                                   
# colgrep-mcp e2e run (warm-1)

corpus: `/Users/me/colgrep-e2e-corpus/click`

| # | Call | Args | Wall ms | is_error | Hits | Text chars | Truncated | Notes |
|--:|:--|:--|--:|:--|--:|--:|:--|:--|
| 1 | `doctor` | `{}` | 62 | False | - | 626 | - |  |
| 2 | `index_status` | `{}` | 181 | False | - | 224 | - |  |
| 3 | `index_build` | `{}` | 51 | False | - | 81 | - |  |
| 4 | `index_status` | `{}` | 61 | False | - | 224 | - |  |
| 5 | `search` | `{"query":"how are command line options parsed into values","limit":5}` | 928 | False | 5 | 1884 | False |  |
| 6 | `search` | `{"query":"decorator that registers a command","pattern":"def command","include":["*.py"...` | 747 | False | 3 | 1258 | False |  |
| 7 | `search` | `{"query":"shell completion","limit":null}` | 767 | False | 15 | 5010 | False | [LIMIT_DEFAULT_APPLIED] limit omitted without pattern: colgrep applies its own default of 15 |
| 8 | `search` | `{"query":"uses of parse_args","pattern":"parse_args","limit":null}` | 774 | False | 3 | 1408 | False |  |
| 9 | `search` | `{"query":"context object lifecycle","include_code":true,"limit":3}` | 757 | False | 3 | 1292 | False |  |
| 10 | `search` | `{"query":"zzqx nonexistent quantum banana","pattern":"zzqxzzqx"}` | 552 | False | 0 | 159 | False | [NO_HITS] no units matched |
| 11 | `find_files` | `{"query":"shell completion","limit":5}` | 747 | False | 5 | 714 | True |  |
| 12 | `expand` | `{"hit_ids":["/Users/me/colgrep-e2e-corpus/click/src/click/parser...` | 1 | False | 3 | 2234 | - |  |
| 13 | `list_indexes` | `{}` | 51 | False | 161 | 24651 | - |  |
| 14 | `resource:colgrep://guide` | `{}` | 3 | False | - | 7944 | - |  |
| 15 | `resource:colgrep://status/Users/me/colgrep-e2e-corpus/click` | `{}` | 29 | False | - | 642 | - |  |
| 16 | `prompt:explore` | `{"question":"how does click parse options?"}` | 2 | False | - | 1017 | - |  |
| 17 | `index_clear` | `{}` | 21 | True | - | 208 | - | ERROR: Error executing tool index_clear: [CONFIRMATION_REQUIRED] Refusing to delete the index for /Users/me/projects |

Median search (a)-(e) wall time: 767 ms (n=5: [747, 757, 767, 774, 928])
location_verified=false count across search (a)-(e): 0/29 hits
index_build progress notifications observed: 1 (first='Index is up to date for /Users/me/colgrep-e2e-corpus/click', last='Index is up to date for /Users/me/colgrep-e2e-corpus/click')
total is_error=True results: 1 (expected: index_clear_noconfirm only)
