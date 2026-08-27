code = '''

@router.post("/knowledge/documents/{document_id}/reject")
def reject_knowledge_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    old_status = doc.status
    doc.status = "REJECTED"
    
    log = AuditLog(
        user_id=current_user.id,
        action="REJECT_DOCUMENT",
        resource="KnowledgeDocument",
        resource_id=document_id,
        success=True,
        details={
            "previous_status": old_status,
            "new_status": "REJECTED",
            "content_hash": doc.content_hash,
            "review_decision": "REJECT"
        }
    )
    db.add(log)
    db.commit()
    return {"message": "Document rejected", "document_id": document_id}
'''

with open("backend/app/api/admin.py", "a", encoding="utf-8") as f:
    f.write(code)
