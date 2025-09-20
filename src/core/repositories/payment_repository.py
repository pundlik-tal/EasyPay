"""
EasyPay Payment Gateway - Payment Repository
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.models.payment import Payment, PaymentStatus
from src.core.exceptions import PaymentNotFoundError, DatabaseError


class PaymentRepository:
    """
    Repository for payment-related database operations.
    
    This class provides methods for CRUD operations on payments,
    including advanced querying, filtering, and pagination.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, payment_data: Dict[str, Any]) -> Payment:
        """
        Create a new payment record.
        
        Args:
            payment_data: Dictionary containing payment data
            
        Returns:
            Payment: Created payment instance
            
        Raises:
            DatabaseError: If creation fails
        """
        try:
            payment = Payment(**payment_data)
            self.session.add(payment)
            await self.session.commit()
            await self.session.refresh(payment)
            return payment
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create payment: {str(e)}")
    
    async def get_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]:
        """
        Get payment by ID.
        
        Args:
            payment_id: Payment UUID
            
        Returns:
            Payment or None if not found
        """
        try:
            result = await self.session.execute(
                select(Payment)
                .options(selectinload(Payment.webhooks), selectinload(Payment.audit_logs))
                .where(Payment.id == payment_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get payment by ID: {str(e)}")
    
    async def get_by_external_id(self, external_id: str) -> Optional[Payment]:
        """
        Get payment by external ID.
        
        Args:
            external_id: External payment identifier
            
        Returns:
            Payment or None if not found
        """
        try:
            result = await self.session.execute(
                select(Payment)
                .options(selectinload(Payment.webhooks), selectinload(Payment.audit_logs))
                .where(Payment.external_id == external_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get payment by external ID: {str(e)}")
    
    async def get_by_authorize_net_id(self, authorize_net_id: str) -> Optional[Payment]:
        """
        Get payment by Authorize.net transaction ID.
        
        Args:
            authorize_net_id: Authorize.net transaction identifier
            
        Returns:
            Payment or None if not found
        """
        try:
            result = await self.session.execute(
                select(Payment)
                .options(selectinload(Payment.webhooks), selectinload(Payment.audit_logs))
                .where(Payment.authorize_net_transaction_id == authorize_net_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get payment by Authorize.net ID: {str(e)}")
    
    async def update(self, payment_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[Payment]:
        """
        Update payment record.
        
        Args:
            payment_id: Payment UUID
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated Payment or None if not found
            
        Raises:
            DatabaseError: If update fails
        """
        try:
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            # First, get the payment to check if it exists
            payment = await self.get_by_id(payment_id)
            if not payment:
                return None
            
            # Update the payment object
            for key, value in update_data.items():
                setattr(payment, key, value)
            
            await self.session.commit()
            await self.session.refresh(payment)
            return payment
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to update payment: {str(e)}")
    
    async def delete(self, payment_id: uuid.UUID) -> bool:
        """
        Delete payment record.
        
        Args:
            payment_id: Payment UUID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            result = await self.session.execute(
                delete(Payment).where(Payment.id == payment_id)
            )
            
            if result.rowcount == 0:
                return False
                
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to delete payment: {str(e)}")
    
    async def list_payments(
        self,
        customer_id: Optional[str] = None,
        status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Dict[str, Any]:
        """
        List payments with filtering and pagination.
        
        Args:
            customer_id: Filter by customer ID
            status: Filter by payment status
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number (1-based)
            per_page: Items per page
            order_by: Field to order by
            order_direction: Order direction (asc/desc)
            
        Returns:
            Dictionary containing payments list and pagination info
        """
        try:
            # Build query
            query = select(Payment)
            
            # Apply filters
            conditions = []
            if customer_id:
                conditions.append(Payment.customer_id == customer_id)
            if status:
                conditions.append(Payment.status == status)
            if start_date:
                conditions.append(Payment.created_at >= start_date)
            if end_date:
                conditions.append(Payment.created_at <= end_date)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply ordering
            order_column = getattr(Payment, order_by, Payment.created_at)
            if order_direction.lower() == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
            
            # Get total count
            count_query = select(func.count(Payment.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await self.session.execute(query)
            payments = result.scalars().all()
            
            # Calculate pagination info
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "payments": list(payments),
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        except Exception as e:
            raise DatabaseError(f"Failed to list payments: {str(e)}")
    
    async def search_payments(
        self,
        search_term: str,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search payments by various fields.
        
        Args:
            search_term: Search term
            page: Page number (1-based)
            per_page: Items per page
            
        Returns:
            Dictionary containing search results and pagination info
        """
        try:
            # Build search conditions
            search_conditions = or_(
                Payment.external_id.ilike(f"%{search_term}%"),
                Payment.customer_id.ilike(f"%{search_term}%"),
                Payment.customer_email.ilike(f"%{search_term}%"),
                Payment.customer_name.ilike(f"%{search_term}%"),
                Payment.description.ilike(f"%{search_term}%"),
                Payment.authorize_net_transaction_id.ilike(f"%{search_term}%")
            )
            
            # Get total count
            count_query = select(func.count(Payment.id)).where(search_conditions)
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()
            
            # Get results
            query = (
                select(Payment)
                .where(search_conditions)
                .order_by(Payment.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            
            result = await self.session.execute(query)
            payments = result.scalars().all()
            
            # Calculate pagination info
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "payments": list(payments),
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "search_term": search_term
            }
        except Exception as e:
            raise DatabaseError(f"Failed to search payments: {str(e)}")
    
    async def get_payment_stats(
        self,
        customer_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get payment statistics.
        
        Args:
            customer_id: Filter by customer ID
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Dictionary containing payment statistics
        """
        try:
            # Build base query
            base_query = select(Payment)
            conditions = []
            
            if customer_id:
                conditions.append(Payment.customer_id == customer_id)
            if start_date:
                conditions.append(Payment.created_at >= start_date)
            if end_date:
                conditions.append(Payment.created_at <= end_date)
            
            if conditions:
                base_query = base_query.where(and_(*conditions))
            
            # Get total count
            count_query = select(func.count(Payment.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await self.session.execute(count_query)
            total_count = total_result.scalar()
            
            # Get total amount
            amount_query = select(func.sum(Payment.amount))
            if conditions:
                amount_query = amount_query.where(and_(*conditions))
            
            amount_result = await self.session.execute(amount_query)
            total_amount = amount_result.scalar() or Decimal('0')
            
            # Get status counts
            status_query = (
                select(Payment.status, func.count(Payment.id))
                .group_by(Payment.status)
            )
            if conditions:
                status_query = status_query.where(and_(*conditions))
            
            status_result = await self.session.execute(status_query)
            status_counts = dict(status_result.fetchall())
            
            return {
                "total_count": total_count,
                "total_amount": float(total_amount),
                "status_counts": status_counts,
                "average_amount": float(total_amount / total_count) if total_count > 0 else 0
            }
        except Exception as e:
            raise DatabaseError(f"Failed to get payment stats: {str(e)}")
    
    async def get_payments_by_customer(self, customer_id: str) -> List[Payment]:
        """
        Get all payments for a customer.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            List of payments for the customer
        """
        try:
            result = await self.session.execute(
                select(Payment)
                .where(Payment.customer_id == customer_id)
                .order_by(Payment.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get payments by customer: {str(e)}")
    
    async def get_payments_by_status(self, status: PaymentStatus) -> List[Payment]:
        """
        Get all payments with a specific status.
        
        Args:
            status: Payment status
            
        Returns:
            List of payments with the specified status
        """
        try:
            result = await self.session.execute(
                select(Payment)
                .where(Payment.status == status)
                .order_by(Payment.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get payments by status: {str(e)}")
