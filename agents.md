# **agents.md**

## **Purpose**
This document defines the rules, structure, and expectations for all AI agents contributing to this repository.  
Agents must follow these guidelines when generating, modifying, or reviewing code, documentation, tests, or infrastructure.

The goal:  
A clean, maintainable, well‑documented **backend API** and **frontend UI**, each running in its own Docker container, with consistent architecture, strong testing, and clear documentation.

---

## **1. Project Structure Requirements**

### **Root Layout**
```
/
├── agents.md
├── README.md
├── docker-compose.yml
├── docs/
├── src/
│   ├── backend/
│   └── frontend/
└── tests/
```

### **Rules**
- **All code MUST live inside `/src/`**  
  - Backend code goes in `/src/backend/`  
  - Frontend code goes in `/src/frontend/`
- **All documentation MUST live in `/docs/`**
- **All unit tests MUST live in `/tests/`**
- **No code should exist outside `/src/` except config files, compose files, and docs.**
- **Folder structure must remain sensible, predictable, and consistent.**

---

## **2. Code Quality & Documentation Rules**

### **Mandatory Comments**
Every file must include:
- A **header comment** explaining the file’s purpose  
- Inline comments explaining non‑trivial logic  
- Clear section headers for readability

### **Mandatory Function Documentation**
Every function must include:
- A docstring describing:
  - What it does  
  - Parameters  
  - Return values  
  - Side effects (DB writes, network calls, etc.)  

No undocumented functions are allowed.

### **Architecture Consistency**
Agents must:
- Follow the existing backend architecture (FastAPI + SQLAlchemy + Alembic)
- Follow the existing frontend architecture (Vue + Vite)
- Maintain async patterns correctly in backend code
- Keep migrations consistent with Alembic conventions
- Avoid rewriting entire files unless necessary

Agents **may be creative**, but must preserve architectural integrity.

---

## **3. Testing Requirements**

### **Unit Tests**
- All tests must be placed in `/tests/`
- Tests should be grouped by service:
  ```
  /tests/backend/
  /tests/frontend/
  ```
- Tests must:
  - Be meaningful  
  - Cover core logic  
  - Include mocks where appropriate  
  - Include API endpoint tests for backend  
  - Include component tests for frontend  

### **Test Coverage**
Agents should aim to increase coverage over time.

---

## **4. Documentation Requirements**

### **Docs Folder**
All documentation must be placed in `/docs/`.

### **README Updates**
Whenever agents:
- Add major features  
- Change architecture  
- Modify Docker setup  
- Add new environment variables  
- Change build/run instructions  

They MUST update:
- `README.md`
- Any relevant docs in `/docs/`

README must always reflect the current state of the project.

---

## **5. Docker Requirements**

### **Containers**
The project must always support:
- **Backend API container**
- **Frontend UI container**

### **Compose Updates**
If agents make major changes:
- Add new services  
- Change ports  
- Add environment variables  
- Modify startup scripts  

They MUST update:
- `docker-compose.yml`
- Example compose files in `/docs/`

### **Entrypoint Scripts**
Agents must ensure:
- Scripts use LF line endings  
- Scripts are POSIX‑compliant  
- Migrations run before backend startup  
- Frontend builds correctly via Vite

---

## **6. Dependency Management**

### **Backend**
Agents must keep:
```
/src/requirements.txt
```
up to date whenever:
- New libraries are added  
- Old libraries are removed  
- Versions change  

### **Frontend**
Agents must update:
```
/src/frontend/package.json
```
when adding or removing dependencies.

---

## **7. Allowed Agent Behavior**

Agents **ARE allowed** to:
- Refactor code  
- Improve architecture  
- Add new modules  
- Add new tests  
- Add new documentation  
- Improve Docker workflows  
- Suggest better patterns  
- Add new features  
- Be creative and propose improvements

Agents **ARE NOT allowed** to:
- Remove documentation  
- Remove tests  
- Introduce undocumented functions  
- Break folder structure  
- Move code outside `/src/`  
- Ignore README updates  
- Ignore Docker updates  
- Rewrite entire files without reason

---

## **8. Editing Rules**

Agents must:
- Produce minimal diffs unless a major refactor is needed  
- Maintain formatting  
- Maintain imports  
- Maintain type hints  
- Keep code readable  
- Keep comments clear  
- Avoid unnecessary complexity  

---

## **9. Safety & Stability Rules**

Agents must:
- Avoid breaking migrations  
- Avoid breaking API contracts  
- Avoid breaking frontend/backend integration  
- Avoid breaking Docker builds  
- Avoid breaking environment variable usage  

If a breaking change is necessary:
- Document it  
- Update README  
- Update compose files  
- Add migration notes in `/docs/`

---

## **10. Final Rule**

Agents should behave like a senior engineer:
- Thoughtful  
- Careful  
- Creative  
- Consistent  
- Well‑documented  
- Architecture‑aware  
- Test‑driven  
