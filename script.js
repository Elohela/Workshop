// Family Genealogy Application
// Data Model and State Management

class FamilyTreeApp {
    constructor() {
        this.familyData = [];
        this.currentEditingId = null;
        this.svg = null;
        this.zoom = null;
        this.g = null;
        this.init();
    }

    init() {
        this.loadData();
        this.setupEventListeners();
        this.renderTree();
        this.updateEmptyState();
    }

    // ===== DATA MANAGEMENT =====

    loadData() {
        const stored = localStorage.getItem('familyTreeData');
        if (stored) {
            this.familyData = JSON.parse(stored);
        }
    }

    saveData() {
        localStorage.setItem('familyTreeData', JSON.stringify(this.familyData));
        this.renderTree();
        this.updateEmptyState();
    }

    generateId() {
        return 'person_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    addPerson(personData) {
        personData.id = this.generateId();
        personData.children = personData.children || [];
        this.familyData.push(personData);
        this.saveData();
        return personData.id;
    }

    updatePerson(id, personData) {
        const index = this.familyData.findIndex(p => p.id === id);
        if (index !== -1) {
            personData.id = id;
            personData.children = personData.children || this.familyData[index].children || [];
            this.familyData[index] = personData;
            this.saveData();
        }
    }

    deletePerson(id) {
        // Remove person from family data
        this.familyData = this.familyData.filter(p => p.id !== id);

        // Clean up references in other people
        this.familyData.forEach(person => {
            if (person.motherId === id) person.motherId = null;
            if (person.fatherId === id) person.fatherId = null;
            if (person.spouseId === id) person.spouseId = null;
            if (person.children) {
                person.children = person.children.filter(childId => childId !== id);
            }
        });

        this.saveData();
    }

    getPerson(id) {
        return this.familyData.find(p => p.id === id);
    }

    getChildren(parentId) {
        return this.familyData.filter(p =>
            p.motherId === parentId || p.fatherId === parentId
        );
    }

    getRootPeople() {
        return this.familyData.filter(p => !p.motherId && !p.fatherId);
    }

    // ===== TREE VISUALIZATION =====

    renderTree() {
        const container = document.getElementById('familyTree');
        const width = container.clientWidth;
        const height = container.clientHeight;

        // Clear existing SVG
        d3.select('#familyTree').selectAll('*').remove();

        if (this.familyData.length === 0) {
            return;
        }

        // Create SVG
        this.svg = d3.select('#familyTree')
            .attr('width', width)
            .attr('height', height);

        // Add zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });

        this.svg.call(this.zoom);

        // Create main group
        this.g = this.svg.append('g');

        // Build tree structure
        const roots = this.getRootPeople();

        if (roots.length === 0) {
            // If no root people, just show all people
            this.renderSimpleLayout();
            return;
        }

        // Create hierarchical layout for each root
        roots.forEach((root, index) => {
            this.renderFamilyBranch(root, index * 300, 100);
        });

        // Center the view
        this.centerView();
    }

    renderFamilyBranch(root, offsetX, offsetY) {
        const hierarchy = this.buildHierarchy(root);

        // Create tree layout
        const treeLayout = d3.tree()
            .nodeSize([180, 150])
            .separation((a, b) => (a.parent === b.parent ? 1 : 1.5));

        const treeData = d3.hierarchy(hierarchy);
        const nodes = treeLayout(treeData);

        // Draw links
        this.g.selectAll('.link-' + root.id)
            .data(nodes.links())
            .enter()
            .append('path')
            .attr('class', 'link')
            .attr('d', d => {
                return `M ${d.source.x + offsetX},${d.source.y + offsetY}
                        C ${d.source.x + offsetX},${(d.source.y + d.target.y) / 2 + offsetY}
                          ${d.target.x + offsetX},${(d.source.y + d.target.y) / 2 + offsetY}
                          ${d.target.x + offsetX},${d.target.y + offsetY}`;
            });

        // Draw spouse links
        this.drawSpouseLinks(nodes, offsetX, offsetY);

        // Draw nodes
        const node = this.g.selectAll('.node-' + root.id)
            .data(nodes.descendants())
            .enter()
            .append('g')
            .attr('class', d => {
                const person = d.data.person;
                let classes = 'node';
                if (person.gender) classes += ' ' + person.gender;
                if (person.deathDate) classes += ' deceased';
                return classes;
            })
            .attr('transform', d => `translate(${d.x + offsetX},${d.y + offsetY})`)
            .on('click', (event, d) => this.onNodeClick(event, d.data.person));

        // Add circles
        node.append('circle')
            .attr('r', 30);

        // Add text labels
        node.append('text')
            .attr('dy', 50)
            .text(d => {
                const person = d.data.person;
                return `${person.firstName} ${person.lastName}`;
            });

        // Add birth year
        node.append('text')
            .attr('dy', 65)
            .attr('font-size', '10px')
            .attr('fill', '#999')
            .text(d => {
                const person = d.data.person;
                if (person.birthDate) {
                    const year = new Date(person.birthDate).getFullYear();
                    return person.deathDate
                        ? `${year} - ${new Date(person.deathDate).getFullYear()}`
                        : `b. ${year}`;
                }
                return '';
            });
    }

    buildHierarchy(person) {
        const children = this.getChildren(person.id);
        return {
            person: person,
            children: children.map(child => this.buildHierarchy(child))
        };
    }

    drawSpouseLinks(nodes, offsetX, offsetY) {
        nodes.descendants().forEach(node => {
            const person = node.data.person;
            if (person.spouseId) {
                const spouse = this.getPerson(person.spouseId);
                if (spouse) {
                    // Find spouse node position
                    const spouseNode = nodes.descendants().find(n => n.data.person.id === spouse.id);
                    if (spouseNode) {
                        this.g.append('path')
                            .attr('class', 'spouse-link')
                            .attr('d', `M ${node.x + offsetX},${node.y + offsetY}
                                       L ${spouseNode.x + offsetX},${spouseNode.y + offsetY}`);
                    }
                }
            }
        });
    }

    renderSimpleLayout() {
        const width = document.getElementById('familyTree').clientWidth;
        const itemsPerRow = Math.floor(width / 200);

        this.familyData.forEach((person, index) => {
            const x = (index % itemsPerRow) * 200 + 100;
            const y = Math.floor(index / itemsPerRow) * 150 + 100;

            const node = this.g.append('g')
                .attr('class', `node ${person.gender} ${person.deathDate ? 'deceased' : ''}`)
                .attr('transform', `translate(${x},${y})`)
                .on('click', () => this.onNodeClick(event, person));

            node.append('circle').attr('r', 30);
            node.append('text')
                .attr('dy', 50)
                .text(`${person.firstName} ${person.lastName}`);
        });

        this.centerView();
    }

    centerView() {
        const bounds = this.g.node().getBBox();
        const parent = this.svg.node().getBoundingClientRect();
        const fullWidth = parent.width;
        const fullHeight = parent.height;
        const width = bounds.width;
        const height = bounds.height;

        const midX = bounds.x + width / 2;
        const midY = bounds.y + height / 2;

        const scale = 0.8 / Math.max(width / fullWidth, height / fullHeight);
        const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];

        this.svg.transition().duration(750).call(
            this.zoom.transform,
            d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
        );
    }

    onNodeClick(event, person) {
        event.stopPropagation();
        this.showPersonModal(person);
    }

    // ===== UI CONTROLS =====

    setupEventListeners() {
        // Add root person button
        document.getElementById('addRootBtn').addEventListener('click', () => {
            this.openPanel();
        });

        // Panel controls
        document.getElementById('closePanel').addEventListener('click', () => {
            this.closePanel();
        });

        document.getElementById('cancelBtn').addEventListener('click', () => {
            this.closePanel();
        });

        // Form submission
        document.getElementById('memberForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveMember();
        });

        // Delete button
        document.getElementById('deleteBtn').addEventListener('click', () => {
            if (confirm('Are you sure you want to delete this person? This cannot be undone.')) {
                this.deletePerson(this.currentEditingId);
                this.closePanel();
            }
        });

        // Add child button
        document.getElementById('addChildBtn').addEventListener('click', () => {
            this.addChildToPerson(this.currentEditingId);
        });

        // Export button
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportData();
        });

        // Import button
        document.getElementById('importBtn').addEventListener('click', () => {
            document.getElementById('importFile').click();
        });

        document.getElementById('importFile').addEventListener('change', (e) => {
            this.importData(e.target.files[0]);
        });

        // Search
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.searchFamily(e.target.value);
        });

        // Zoom controls
        document.getElementById('zoomIn').addEventListener('click', () => {
            this.svg.transition().call(this.zoom.scaleBy, 1.3);
        });

        document.getElementById('zoomOut').addEventListener('click', () => {
            this.svg.transition().call(this.zoom.scaleBy, 0.7);
        });

        document.getElementById('resetZoom').addEventListener('click', () => {
            this.centerView();
        });

        document.getElementById('fitView').addEventListener('click', () => {
            this.centerView();
        });

        // Modal controls
        document.getElementById('closeModal').addEventListener('click', () => {
            this.closeModal();
        });

        document.getElementById('editPersonBtn').addEventListener('click', () => {
            const personId = document.getElementById('editPersonBtn').dataset.personId;
            const person = this.getPerson(personId);
            this.closeModal();
            this.openPanel(person);
        });

        document.getElementById('addChildToPersonBtn').addEventListener('click', () => {
            const personId = document.getElementById('addChildToPersonBtn').dataset.personId;
            this.closeModal();
            this.addChildToPerson(personId);
        });

        document.getElementById('addSpouseBtn').addEventListener('click', () => {
            const personId = document.getElementById('addSpouseBtn').dataset.personId;
            this.closeModal();
            this.addSpouseToPerson(personId);
        });

        // Close modal when clicking outside
        document.getElementById('personModal').addEventListener('click', (e) => {
            if (e.target.id === 'personModal') {
                this.closeModal();
            }
        });
    }

    // ===== PANEL MANAGEMENT =====

    openPanel(person = null) {
        const panel = document.getElementById('sidePanel');
        const form = document.getElementById('memberForm');
        const title = document.getElementById('panelTitle');
        const deleteBtn = document.getElementById('deleteBtn');

        form.reset();
        this.currentEditingId = person ? person.id : null;

        if (person) {
            title.textContent = 'Edit Family Member';
            deleteBtn.style.display = 'block';

            // Fill form with person data
            document.getElementById('memberId').value = person.id;
            document.getElementById('firstName').value = person.firstName || '';
            document.getElementById('lastName').value = person.lastName || '';
            document.getElementById('gender').value = person.gender || '';
            document.getElementById('birthDate').value = person.birthDate || '';
            document.getElementById('deathDate').value = person.deathDate || '';
            document.getElementById('photo').value = person.photo || '';
            document.getElementById('bio').value = person.bio || '';
            document.getElementById('notes').value = person.notes || '';
        } else {
            title.textContent = 'Add Family Member';
            deleteBtn.style.display = 'none';
        }

        // Update relationship dropdowns
        this.updateRelationshipSelects(person);

        panel.classList.add('active');
    }

    closePanel() {
        document.getElementById('sidePanel').classList.remove('active');
        this.currentEditingId = null;
    }

    updateRelationshipSelects(currentPerson) {
        const motherId = currentPerson?.motherId || '';
        const fatherId = currentPerson?.fatherId || '';
        const spouseId = currentPerson?.spouseId || '';

        // Update mother select
        const motherSelect = document.getElementById('mother');
        motherSelect.innerHTML = '<option value="">Select mother...</option>';
        this.familyData
            .filter(p => p.gender === 'female' && (!currentPerson || p.id !== currentPerson.id))
            .forEach(p => {
                const option = document.createElement('option');
                option.value = p.id;
                option.textContent = `${p.firstName} ${p.lastName}`;
                option.selected = p.id === motherId;
                motherSelect.appendChild(option);
            });

        // Update father select
        const fatherSelect = document.getElementById('father');
        fatherSelect.innerHTML = '<option value="">Select father...</option>';
        this.familyData
            .filter(p => p.gender === 'male' && (!currentPerson || p.id !== currentPerson.id))
            .forEach(p => {
                const option = document.createElement('option');
                option.value = p.id;
                option.textContent = `${p.firstName} ${p.lastName}`;
                option.selected = p.id === fatherId;
                fatherSelect.appendChild(option);
            });

        // Update spouse select
        const spouseSelect = document.getElementById('spouse');
        spouseSelect.innerHTML = '<option value="">Select spouse...</option>';
        this.familyData
            .filter(p => !currentPerson || p.id !== currentPerson.id)
            .forEach(p => {
                const option = document.createElement('option');
                option.value = p.id;
                option.textContent = `${p.firstName} ${p.lastName}`;
                option.selected = p.id === spouseId;
                spouseSelect.appendChild(option);
            });

        // Update children list
        this.updateChildrenList(currentPerson);
    }

    updateChildrenList(currentPerson) {
        const childrenList = document.getElementById('childrenList');
        childrenList.innerHTML = '';

        if (currentPerson) {
            const children = this.getChildren(currentPerson.id);
            children.forEach(child => {
                const childItem = document.createElement('div');
                childItem.className = 'child-item';
                childItem.innerHTML = `
                    <span>${child.firstName} ${child.lastName}</span>
                    <button type="button" onclick="app.removeChild('${currentPerson.id}', '${child.id}')">Remove</button>
                `;
                childrenList.appendChild(childItem);
            });
        }
    }

    removeChild(parentId, childId) {
        const child = this.getPerson(childId);
        const parent = this.getPerson(parentId);

        if (child && parent) {
            if (parent.gender === 'female') {
                child.motherId = null;
            } else if (parent.gender === 'male') {
                child.fatherId = null;
            }
            this.updatePerson(childId, child);
            this.updateChildrenList(parent);
        }
    }

    saveMember() {
        const formData = {
            firstName: document.getElementById('firstName').value.trim(),
            lastName: document.getElementById('lastName').value.trim(),
            gender: document.getElementById('gender').value,
            birthDate: document.getElementById('birthDate').value,
            deathDate: document.getElementById('deathDate').value,
            photo: document.getElementById('photo').value.trim(),
            bio: document.getElementById('bio').value.trim(),
            notes: document.getElementById('notes').value.trim(),
            motherId: document.getElementById('mother').value || null,
            fatherId: document.getElementById('father').value || null,
            spouseId: document.getElementById('spouse').value || null
        };

        if (this.currentEditingId) {
            // Update existing person
            const existingPerson = this.getPerson(this.currentEditingId);
            formData.children = existingPerson.children || [];
            this.updatePerson(this.currentEditingId, formData);

            // Update spouse relationship
            if (formData.spouseId) {
                const spouse = this.getPerson(formData.spouseId);
                if (spouse) {
                    spouse.spouseId = this.currentEditingId;
                    this.updatePerson(spouse.id, spouse);
                }
            }
        } else {
            // Add new person
            this.addPerson(formData);
        }

        this.closePanel();
    }

    addChildToPerson(parentId) {
        const parent = this.getPerson(parentId);
        if (!parent) return;

        this.openPanel();

        // Pre-fill parent information
        if (parent.gender === 'female') {
            setTimeout(() => document.getElementById('mother').value = parentId, 100);
        } else if (parent.gender === 'male') {
            setTimeout(() => document.getElementById('father').value = parentId, 100);
        }
    }

    addSpouseToPerson(personId) {
        this.openPanel();
        setTimeout(() => document.getElementById('spouse').value = personId, 100);
    }

    // ===== MODAL =====

    showPersonModal(person) {
        const modal = document.getElementById('personModal');

        document.getElementById('modalName').textContent = `${person.firstName} ${person.lastName}`;

        // Photo
        const photoImg = document.getElementById('modalPhoto');
        if (person.photo) {
            photoImg.src = person.photo;
            photoImg.style.display = 'block';
        } else {
            photoImg.style.display = 'none';
        }

        // Birth and death
        document.getElementById('modalBirth').textContent = person.birthDate
            ? new Date(person.birthDate).toLocaleDateString()
            : 'Unknown';

        document.getElementById('modalDeath').textContent = person.deathDate
            ? new Date(person.deathDate).toLocaleDateString()
            : 'Living';

        // Age
        const age = this.calculateAge(person);
        document.getElementById('modalAge').textContent = age;

        // Bio
        const bioRow = document.getElementById('modalBioRow');
        if (person.bio) {
            document.getElementById('modalBio').textContent = person.bio;
            bioRow.style.display = 'block';
        } else {
            bioRow.style.display = 'none';
        }

        // Notes
        const notesRow = document.getElementById('modalNotesRow');
        if (person.notes) {
            document.getElementById('modalNotes').textContent = person.notes;
            notesRow.style.display = 'block';
        } else {
            notesRow.style.display = 'none';
        }

        // Store person ID for action buttons
        document.getElementById('editPersonBtn').dataset.personId = person.id;
        document.getElementById('addChildToPersonBtn').dataset.personId = person.id;
        document.getElementById('addSpouseBtn').dataset.personId = person.id;

        modal.classList.add('active');
    }

    closeModal() {
        document.getElementById('personModal').classList.remove('active');
    }

    calculateAge(person) {
        if (!person.birthDate) return 'Unknown';

        const birth = new Date(person.birthDate);
        const end = person.deathDate ? new Date(person.deathDate) : new Date();
        const age = end.getFullYear() - birth.getFullYear();

        if (person.deathDate) {
            return `${age} years (deceased)`;
        } else {
            return `${age} years old`;
        }
    }

    // ===== SEARCH =====

    searchFamily(query) {
        if (!query.trim()) {
            // Reset highlight
            this.renderTree();
            return;
        }

        const results = this.familyData.filter(person => {
            const searchText = `${person.firstName} ${person.lastName} ${person.bio || ''} ${person.notes || ''}`.toLowerCase();
            return searchText.includes(query.toLowerCase());
        });

        // Highlight matching nodes
        d3.selectAll('.node')
            .style('opacity', d => {
                if (!d || !d.data || !d.data.person) return 1;
                const person = d.data.person;
                return results.find(p => p.id === person.id) ? 1 : 0.3;
            });
    }

    // ===== EXPORT/IMPORT =====

    exportData() {
        const dataStr = JSON.stringify(this.familyData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);

        const link = document.createElement('a');
        link.href = url;
        link.download = `family-tree-${new Date().toISOString().split('T')[0]}.json`;
        link.click();

        URL.revokeObjectURL(url);
    }

    importData(file) {
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                if (Array.isArray(data)) {
                    if (confirm('This will replace your current family tree. Continue?')) {
                        this.familyData = data;
                        this.saveData();
                    }
                } else {
                    alert('Invalid file format');
                }
            } catch (error) {
                alert('Error reading file: ' + error.message);
            }
        };
        reader.readAsText(file);
    }

    // ===== UTILITY =====

    updateEmptyState() {
        const emptyState = document.getElementById('emptyState');
        emptyState.style.display = this.familyData.length === 0 ? 'block' : 'none';
    }
}

// Initialize app when DOM is ready
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new FamilyTreeApp();
    console.log('Family Genealogy Map initialized');
});

// Handle window resize
window.addEventListener('resize', () => {
    if (app) {
        app.renderTree();
    }
});
