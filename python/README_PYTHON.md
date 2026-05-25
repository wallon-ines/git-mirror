# Git Mirror - Python Port

> Une version Python du projet **git-mirror** (originalement en Rust) pour des fins d'apprentissage.

**Projet original**: https://github.com/bachp/git-mirror

## 📚 But pédagogique

Ce projet a été porté de **Rust vers Python** pour:
- Comprendre les concepts de git-mirror
- Apprendre la structure d'un projet en Rust
- Comparer les idiomes Rust vs Python

## 🏗️ Architecture

### Structure du code Rust → Python

| Fichier Rust | Fichier Python | But |
|---|---|---|
| `src/main.rs` | `git_mirror/main.py` | CLI avec argparse |
| `src/lib.rs` | `git_mirror/mirror.py` | Logique principale |
| `src/git.rs` | `git_mirror/git_wrapper.py` | Wrapper git |
| `src/error.rs` | `git_mirror/errors.py` | Gestion des erreurs |
| `src/provider/mod.rs` | `git_mirror/provider/__init__.py` | Interface Provider |
| `src/provider/gitlab.rs` | `git_mirror/provider/gitlab.py` | Provider GitLab |
| `src/provider/github.rs` | `git_mirror/provider/github.py` | Provider GitHub |

### Concepts clés

#### 1. **Traits Rust** → **Classes abstraites Python**

**Rust:**
```rust
pub trait Provider {
    fn get_mirror_repos(&self) -> Result<Vec<MirrorResult>, String>;
    fn get_label(&self) -> String;
}
```

**Python:**
```python
from abc import ABC, abstractmethod

class Provider(ABC):
    @abstractmethod
    def get_mirror_repos(self) -> List[Union[Mirror, MirrorError]]:
        pass
    
    @abstractmethod
    def get_label(self) -> str:
        pass
```

#### 2. **Gestion des erreurs**

**Rust** utilise `Result<T, E>` pour les erreurs:
```rust
pub enum GitError {
    CommandError { cmd_str: String, err: io::Error },
    GitCommandError { code: i32, stderr: String, cmd_str: String },
    GitCommandTimeout { cmd_str: String, timeout: Duration },
}
```

**Python** utilise des exceptions personnalisées:
```python
class GitCommandError(GitError):
    def __init__(self, cmd: str, code: int, stderr: str):
        self.cmd = cmd
        self.code = code
        self.stderr = stderr
```

#### 3. **Exécution parallèle**

**Rust** utilise `rayon` pour le parallélisme:
```rust
let results = v
    .par_iter()
    .enumerate()
    .map(|(i, x)| { /* process */ })
    .collect::<Vec<_>>();
```

**Python** utilisera `concurrent.futures` ou `multiprocessing`:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=worker_count) as executor:
    results = list(executor.map(process_repo, repos))
```

#### 4. **Configuration/Options**

**Rust:**
```rust
pub struct MirrorOptions {
    pub mirror_dir: PathBuf,
    pub dry_run: bool,
    // ...
}
```

**Python:**
```python
@dataclass
class MirrorOptions:
    mirror_dir: Path
    dry_run: bool = False
    # ...
```

## 🔍 Comparaison des patterns

### Parsing YAML

**Rust:**
```rust
let desc = serde_yaml::from_str::<Desc>(&p.description)
    .map_err(|e| MirrorError::Description(p.web_url, e))?;
```

**Python:**
```python
try:
    repo_desc = RepositoryDescription.from_yaml(description)
except ValueError as e:
    mirrors.append(DescriptionError(web_url, e))
```

### Exécution de commandes

**Rust:**
```rust
let output = Command::new(self.executable.clone())
    .args(["clone", "--mirror"])
    .arg(origin)
    .arg(repo_dir)
    .output()?;
```

**Python:**
```python
result = subprocess.run(
    [self.executable, "clone", "--mirror", origin, str(repo_dir)],
    capture_output=True,
    timeout=self.timeout,
)
```

## 📦 Installation

```bash
cd python
pip install -r requirements.txt
```

## 🚀 Utilisation

```bash
export PRIVATE_TOKEN="<token>"
python -m git_mirror -g mirror-test
```

## 🎓 Concepts Rust à étudier

1. **Ownership & Borrowing** → Gestion manuelle de la mémoire
2. **Traits** → Interfaces/contrats de code
3. **Pattern Matching** → Similar aux switch statements
4. **Error Handling** → `Result` vs Exceptions
5. **Generics** → Templating de type
6. **Lifetimes** → Validité des références

## 📝 Notes d'apprentissage

### Type System
- Rust est **fortement typé** à la compilation
- Python utilise l'**inférence de type** à l'exécution
- Rust force à gérer les erreurs explicitement

### Concurrence
- Rust garantit la **thread-safety** à la compilation
- Python utilise le **GIL** (Global Interpreter Lock)
- Rayon (Rust) vs ThreadPoolExecutor (Python)

### Memory Management
- Rust: **Ownership system** (no garbage collector)
- Python: **Garbage collection** automatique
- Rust force à penser à la durée de vie des objets

## 🔗 Ressources

- [Rust Book](https://doc.rust-lang.org/book/)
- [The Rustlings Course](https://github.com/rust-lang/rustlings)
- [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
- [Original git-mirror](https://github.com/bachp/git-mirror)

## 📄 Licence

MIT (comme le projet original)
